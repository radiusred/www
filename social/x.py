"""X: OAuth 1.0a user context (HMAC-SHA1, signed in the stdlib) and one post.

The tokens are generated once for the account with Read and write and never
expire or rotate, so nothing here writes back to the env file. Links go
inline in the body (the milestone Decision on radiusred/ops#28): there is no
card and no reply path.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets as _secrets
import time
import unicodedata

from .transport import ApiError, Response

API = "https://api.x.com"
CONSOLE = "https://console.x.com/"
# X's weighted count (twitter-text config v3): 280, every URL 23 whatever its
# length, code points in these ranges 1, everything else 2 — CJK included —
# and an emoji sequence 2 as one. docs.x.com "Counting characters".
MAX_WEIGHTED = 280
URL_WEIGHT = 23
LIGHT_RANGES = ((0, 4351), (8192, 8205), (8208, 8223), (8242, 8247))
URL_RE = re.compile(r"https?://[^\s<>()\[\]\"']+")
TRAILING_PUNCT = ".,;:!?'\")"

# The emoji set is the Unicode emoji blocks, not twitter-text's generated
# regex: pictographs and emoticons, dingbats and miscellaneous symbols,
# regional indicators, plus the text-default symbols only when a VS16 asks
# for the emoji presentation.
_EMOJI_BLOCKS = ((0x1F000, 0x1FAFF), (0x2600, 0x27BF), (0x2300, 0x23FF), (0x2B00, 0x2BFF),
                 (0x2194, 0x21AA), (0x25AA, 0x25FE), (0x2934, 0x2935))
_EMOJI_POINTS = {0x24C2, 0x3030, 0x303D, 0x3297, 0x3299}
_EMOJI_WITH_VS16 = {0x00A9, 0x00AE, 0x203C, 0x2049, 0x2122, 0x2139}
_VS16, _ZWJ, _KEYCAP = 0xFE0F, 0x200D, 0x20E3
_SKIN = (0x1F3FB, 0x1F3FF)
_TAGS = (0xE0020, 0xE007F)
_REGIONAL = (0x1F1E6, 0x1F1FF)


class OutOfCredits(ApiError):
    """X's pay-per-use refusal: the account has no credits. HTTP 402, or a
    problem whose type/title/detail names credits — X's reference documents
    neither, so the match is defensive."""

    def __init__(self, what: str, response: Response):
        detail = response.body.decode("utf-8", "replace")[:300]
        Exception.__init__(
            self,
            f"{what}: out of credits — the X account is pay-per-use and its balance is spent; "
            f"buy credits in the X Developer Console ({CONSOLE}) and retry "
            f"(HTTP {response.status} {detail})".rstrip(),
        )
        self.response = response


def out_of_credits(response: Response) -> bool:
    if response.status == 402:
        return True
    try:
        problem = response.json()
    except ValueError:
        return False
    if not isinstance(problem, dict):
        return False
    parts = [str(problem.get(k, "")) for k in ("type", "title", "detail")]
    for err in problem.get("errors") or []:
        if isinstance(err, dict):
            parts.extend(str(err.get(k, "")) for k in ("title", "message"))
    return "credit" in " ".join(parts).lower()


# --- the weighted count ------------------------------------------------


def _in(cp: int, ranges) -> bool:
    return any(a <= cp <= b for a, b in ranges)


def _emoji_end(text: str, i: int) -> int:
    """The index after the emoji sequence starting at ``i``, or ``i`` when
    no emoji starts there."""
    n = len(text)
    cp = ord(text[i])
    nxt = ord(text[i + 1]) if i + 1 < n else None
    if text[i] in "0123456789#*":
        j = i + 1
        if nxt == _VS16:
            j += 1
        if j < n and ord(text[j]) == _KEYCAP:
            return j + 1
        return i
    if _in(cp, (_REGIONAL,)):
        return i + 2 if nxt is not None and _in(nxt, (_REGIONAL,)) else i + 1
    if cp in _EMOJI_WITH_VS16:
        return i + 2 if nxt == _VS16 else i
    if not (_in(cp, _EMOJI_BLOCKS) or cp in _EMOJI_POINTS):
        return i
    j = i + 1
    while j < n:
        cp = ord(text[j])
        if cp == _VS16 or _in(cp, (_SKIN, _TAGS)):
            j += 1
        elif cp == _ZWJ and j + 1 < n and _emoji_end(text, j + 1) > j + 1:
            j = _emoji_end(text, j + 1)
        else:
            break
    return j


def _weigh(text: str) -> int:
    total, i = 0, 0
    while i < len(text):
        end = _emoji_end(text, i)
        if end > i:
            total += 2
            i = end
            continue
        total += 1 if _in(ord(text[i]), LIGHT_RANGES) else 2
        i += 1
    return total


def weighted_len(text: str) -> int:
    """X's weighted length of ``text``: NFC, URLs 23 each, then the per-code-
    point weights with emoji sequences as 2."""
    text = unicodedata.normalize("NFC", text)
    total, pos = 0, 0
    for match in URL_RE.finditer(text):
        url = match.group().rstrip(TRAILING_PUNCT)
        total += _weigh(text[pos : match.start()]) + URL_WEIGHT
        pos = match.start() + len(url)
    return total + _weigh(text[pos:])


def build_post(text: str) -> dict:
    """The ``POST /2/tweets`` body. Refuses empty and over-length text here,
    before any network call — X would refuse it too, after billing the try."""
    text = unicodedata.normalize("NFC", text.strip())
    if not text:
        raise ValueError("post text is empty")
    count = weighted_len(text)
    if count > MAX_WEIGHTED:
        raise ValueError(
            f"post is {count} weighted characters; X allows {MAX_WEIGHTED} (every URL counts as {URL_WEIGHT})"
        )
    return {"text": text}


# --- OAuth 1.0a ----------------------------------------------------------


def percent_encode(value: str) -> str:
    """RFC 3986 unreserved characters only, as OAuth 1.0a requires."""
    return "".join(
        ch if ch.isascii() and (ch.isalnum() or ch in "-._~") else "".join(f"%{b:02X}" for b in ch.encode())
        for ch in value
    )


def signature_base_string(method: str, url: str, params: dict[str, str]) -> str:
    """Method, base URL and the sorted, encoded parameters — query and
    form parameters plus the oauth_* ones. A JSON body is not a parameter."""
    pairs = sorted((percent_encode(k), percent_encode(v)) for k, v in params.items())
    parameter_string = "&".join(f"{k}={v}" for k, v in pairs)
    return "&".join([method.upper(), percent_encode(url), percent_encode(parameter_string)])


def sign(method: str, url: str, params: dict[str, str], consumer_secret: str, token_secret: str) -> str:
    key = f"{percent_encode(consumer_secret)}&{percent_encode(token_secret)}".encode()
    digest = hmac.new(key, signature_base_string(method, url, params).encode(), hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


def authorization_header(
    method: str,
    url: str,
    consumer_key: str,
    consumer_secret: str,
    token: str,
    token_secret: str,
    query: dict[str, str] | None = None,
    nonce: str | None = None,
    timestamp: int | None = None,
) -> str:
    oauth = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": nonce or _secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time()) if timestamp is None else timestamp),
        "oauth_token": token,
        "oauth_version": "1.0",
    }
    oauth["oauth_signature"] = sign(method, url, {**(query or {}), **oauth}, consumer_secret, token_secret)
    return "OAuth " + ", ".join(f'{k}="{percent_encode(v)}"' for k, v in sorted(oauth.items()))


class X:
    def __init__(self, transport, handle: str, api_key: str, api_secret: str, access_token: str, access_token_secret: str):
        self.transport = transport
        self.handle = handle.lstrip("@")
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret

    def _request(self, what: str, method: str, path: str, body: dict | None = None) -> Response:
        url = f"{API}{path}"
        headers = {
            "Authorization": authorization_header(
                method, url, self.api_key, self.api_secret, self.access_token, self.access_token_secret
            )
        }
        payload = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            payload = json.dumps(body, ensure_ascii=False).encode()
        resp = self.transport(method, url, headers, payload)
        if out_of_credits(resp):
            raise OutOfCredits(what, resp)
        if not resp.ok:
            raise ApiError(what, resp)
        return resp

    def me(self) -> dict:
        """``GET /2/users/me`` — the ``data`` object: ``id``, ``name``, ``username``."""
        return self._request("X check failed", "GET", "/2/users/me").json().get("data", {})

    def post_request(self, body: dict) -> dict:
        return {"method": "POST", "url": f"{API}/2/tweets", "body": body}

    def post(self, body: dict) -> dict:
        data = self._request("X post failed", "POST", "/2/tweets", body).json().get("data", {})
        post_id = data.get("id", "")
        return {"id": post_id, "url": f"https://x.com/{self.handle}/status/{post_id}" if post_id else ""}
