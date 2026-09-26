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
# and an emoji sequence 2 as one. docs.x.com "Counting characters";
# https://github.com/twitter/twitter-text/blob/master/config/v3.json.
MAX_WEIGHTED = 280
URL_WEIGHT = 23
LIGHT_RANGES = ((0, 4351), (8192, 8205), (8208, 8223), (8242, 8247))
URL_RE = re.compile(r"https?://[^\s<>()\[\]\"']+")
# A bare ``label.tld[/path]`` X may autolink (``radiusred.uk``). Without
# twitter-text's TLD table the guard cannot know whether X will, so a
# candidate is weighed as the larger of its literal weight and 23: never
# under. Not preceded by a word character, ``@`` (an address), ``/`` or a
# dot; labels are DNS-shaped; the TLD is letters.
BARE_URL_RE = re.compile(
    r"(?<![\w@./-])(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}(?:/[^\s<>()\[\]\"']*)?(?![\w-])",
    re.IGNORECASE,
)
TRAILING_PUNCT = ".,;:!?'\")"

# The emoji set is Unicode's ``Emoji=Yes`` property (emoji-data.txt, 15.1),
# not twitter-text's generated regex. A code point in a light range weighs 1
# unless it starts an emoji presentation sequence (a keycap, or ``©``/``®``
# with VS16); an emoji outside the light ranges absorbs its VS16, skin tone,
# tag and ZWJ continuations and the sequence weighs 2 as one. A symbol that
# is not an emoji (``⌘``) absorbs nothing, so a stray modifier after it is
# weighed on its own: the guard may over-count, never under.
EMOJI_RANGES = (
    (0x0023, 0x0023), (0x002A, 0x002A), (0x0030, 0x0039), (0x00A9, 0x00A9), (0x00AE, 0x00AE),
    (0x203C, 0x203C), (0x2049, 0x2049), (0x2122, 0x2122), (0x2139, 0x2139), (0x2194, 0x2199),
    (0x21A9, 0x21AA), (0x231A, 0x231B), (0x2328, 0x2328), (0x23CF, 0x23CF), (0x23E9, 0x23F3),
    (0x23F8, 0x23FA), (0x24C2, 0x24C2), (0x25AA, 0x25AB), (0x25B6, 0x25B6), (0x25C0, 0x25C0),
    (0x25FB, 0x25FE), (0x2600, 0x2604), (0x260E, 0x260E), (0x2611, 0x2611), (0x2614, 0x2615),
    (0x2618, 0x2618), (0x261D, 0x261D), (0x2620, 0x2620), (0x2622, 0x2623), (0x2626, 0x2626),
    (0x262A, 0x262A), (0x262E, 0x262F), (0x2638, 0x263A), (0x2640, 0x2640), (0x2642, 0x2642),
    (0x2648, 0x2653), (0x265F, 0x2660), (0x2663, 0x2663), (0x2665, 0x2666), (0x2668, 0x2668),
    (0x267B, 0x267B), (0x267E, 0x267F), (0x2692, 0x2697), (0x2699, 0x2699), (0x269B, 0x269C),
    (0x26A0, 0x26A1), (0x26A7, 0x26A7), (0x26AA, 0x26AB), (0x26B0, 0x26B1), (0x26BD, 0x26BE),
    (0x26C4, 0x26C5), (0x26C8, 0x26C8), (0x26CE, 0x26CF), (0x26D1, 0x26D1), (0x26D3, 0x26D4),
    (0x26E9, 0x26EA), (0x26F0, 0x26F5), (0x26F7, 0x26FA), (0x26FD, 0x26FD), (0x2702, 0x2702),
    (0x2705, 0x2705), (0x2708, 0x270D), (0x270F, 0x270F), (0x2712, 0x2712), (0x2714, 0x2714),
    (0x2716, 0x2716), (0x271D, 0x271D), (0x2721, 0x2721), (0x2728, 0x2728), (0x2733, 0x2734),
    (0x2744, 0x2744), (0x2747, 0x2747), (0x274C, 0x274C), (0x274E, 0x274E), (0x2753, 0x2755),
    (0x2757, 0x2757), (0x2763, 0x2764), (0x2795, 0x2797), (0x27A1, 0x27A1), (0x27B0, 0x27B0),
    (0x27BF, 0x27BF), (0x2934, 0x2935), (0x2B05, 0x2B07), (0x2B1B, 0x2B1C), (0x2B50, 0x2B50),
    (0x2B55, 0x2B55), (0x3030, 0x3030), (0x303D, 0x303D), (0x3297, 0x3297), (0x3299, 0x3299),
    (0x1F004, 0x1F004), (0x1F0CF, 0x1F0CF), (0x1F170, 0x1F171), (0x1F17E, 0x1F17F), (0x1F18E,
    0x1F18E), (0x1F191, 0x1F19A), (0x1F1E6, 0x1F1FF), (0x1F201, 0x1F202), (0x1F21A, 0x1F21A),
    (0x1F22F, 0x1F22F), (0x1F232, 0x1F23A), (0x1F250, 0x1F251), (0x1F300, 0x1F321), (0x1F324,
    0x1F393), (0x1F396, 0x1F397), (0x1F399, 0x1F39B), (0x1F39E, 0x1F3F0), (0x1F3F3, 0x1F3F5),
    (0x1F3F7, 0x1F4FD), (0x1F4FF, 0x1F53D), (0x1F549, 0x1F54E), (0x1F550, 0x1F567), (0x1F56F,
    0x1F570), (0x1F573, 0x1F57A), (0x1F587, 0x1F587), (0x1F58A, 0x1F58D), (0x1F590, 0x1F590),
    (0x1F595, 0x1F596), (0x1F5A4, 0x1F5A5), (0x1F5A8, 0x1F5A8), (0x1F5B1, 0x1F5B2), (0x1F5BC,
    0x1F5BC), (0x1F5C2, 0x1F5C4), (0x1F5D1, 0x1F5D3), (0x1F5DC, 0x1F5DE), (0x1F5E1, 0x1F5E1),
    (0x1F5E3, 0x1F5E3), (0x1F5E8, 0x1F5E8), (0x1F5EF, 0x1F5EF), (0x1F5F3, 0x1F5F3), (0x1F5FA,
    0x1F64F), (0x1F680, 0x1F6C5), (0x1F6CB, 0x1F6D2), (0x1F6D5, 0x1F6D7), (0x1F6DC, 0x1F6E5),
    (0x1F6E9, 0x1F6E9), (0x1F6EB, 0x1F6EC), (0x1F6F0, 0x1F6F0), (0x1F6F3, 0x1F6FC), (0x1F7E0,
    0x1F7EB), (0x1F7F0, 0x1F7F0), (0x1F90C, 0x1F93A), (0x1F93C, 0x1F945), (0x1F947, 0x1F9FF),
    (0x1FA70, 0x1FA7C), (0x1FA80, 0x1FA88), (0x1FA90, 0x1FABD), (0x1FABF, 0x1FAC5), (0x1FACE,
    0x1FADB), (0x1FAE0, 0x1FAE8), (0x1FAF0, 0x1FAF8)
)
_VS16, _ZWJ, _KEYCAP = 0xFE0F, 0x200D, 0x20E3
_SKIN = (0x1F3FB, 0x1F3FF)
_TAGS = (0xE0020, 0xE007F)
_REGIONAL = (0x1F1E6, 0x1F1FF)

# X's pay-per-use refusal. The problem type reported on the developer forum
# is ``https://api.x.com/2/problems/credits-depleted``; titles and details
# vary (``Payment Required`` / ``credits depleted``, ``CreditsDepleted``,
# ``does not have any credits``). Matched positively: a 402 or 4xx that
# says something else — a billing profile, a credit card — is not this.
CREDITS_PROBLEM_TYPE = "credits-depleted"
CREDITS_RE = re.compile(
    r"credits?[\s_-]*(depleted|exhausted)"
    r"|creditsdepleted"
    r"|(insufficient|depleted|exhausted|no|not enough|zero|out of|negative)\s+credits?\b(?!\s+card)"
    r"|(does|do|did)\s+not\s+have\s+(any\s+)?credits?\b"
    r"|credits?\s+balance\s+(is\s+)?(zero|spent|negative|exhausted|empty|depleted)"
)


class OutOfCredits(ApiError):
    """X's pay-per-use refusal: the account's credits are depleted."""

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
    """True when the response says the credits are depleted: the
    ``credits-depleted`` problem type, or a title/detail/errors[] phrase
    saying so. A bare 402 with no such body is not enough on its own."""
    try:
        problem = response.json()
    except ValueError:
        return False
    if not isinstance(problem, dict):
        return False
    ptype = str(problem.get("type", "")).lower().rstrip("/")
    if ptype == CREDITS_PROBLEM_TYPE or ptype.endswith("/" + CREDITS_PROBLEM_TYPE):
        return True
    texts = [str(problem.get(k, "")) for k in ("title", "detail")]
    for err in problem.get("errors") or []:
        if isinstance(err, dict):
            texts.extend(str(err.get(k, "")) for k in ("title", "message", "detail"))
    return any(CREDITS_RE.search(t.lower()) for t in texts)


# --- the weighted count ------------------------------------------------


def _in(cp: int, ranges) -> bool:
    return any(a <= cp <= b for a, b in ranges)


def _absorb(text: str, j: int) -> int:
    """Extend an emoji sequence from ``j`` over VS16, skin tones, tags and
    ZWJ-joined emoji; return the index after it."""
    n = len(text)
    while j < n:
        cp = ord(text[j])
        if cp == _VS16 or _in(cp, (_SKIN, _TAGS)):
            j += 1
        elif cp == _ZWJ and j + 1 < n and _sequence_end(text, j + 1) > j + 1:
            j = _sequence_end(text, j + 1)
        else:
            break
    return j


def _sequence_end(text: str, i: int) -> int:
    """The index after the emoji sequence starting at ``i``, or ``i`` when
    none starts there."""
    n = len(text)
    cp = ord(text[i])
    nxt = ord(text[i + 1]) if i + 1 < n else None
    if text[i] in "0123456789#*":  # keycap: base, optional VS16, U+20E3
        j = i + 2 if nxt == _VS16 else i + 1
        return j + 1 if j < n and ord(text[j]) == _KEYCAP else i
    if not _in(cp, EMOJI_RANGES):
        return i
    if _in(cp, LIGHT_RANGES):  # © and ®: 1 as text, an emoji only with VS16
        return _absorb(text, i + 2) if nxt == _VS16 else i
    if _in(cp, (_REGIONAL,)):  # a flag is a pair
        return i + 2 if nxt is not None and _in(nxt, (_REGIONAL,)) else i + 1
    return _absorb(text, i + 1)


def _weigh(text: str) -> int:
    total, i = 0, 0
    while i < len(text):
        end = _sequence_end(text, i)
        if end > i:
            total += 2
            i = end
            continue
        total += 1 if _in(ord(text[i]), LIGHT_RANGES) else 2
        i += 1
    return total


def _url_spans(text: str) -> list[tuple[int, int, int]]:
    """(start, end, weight) for every URL: 23 for one with a scheme, the
    larger of literal and 23 for a bare domain candidate."""
    spans = []
    for match in URL_RE.finditer(text):
        url = match.group().rstrip(TRAILING_PUNCT)
        spans.append((match.start(), match.start() + len(url), URL_WEIGHT))
    for match in BARE_URL_RE.finditer(text):
        candidate = match.group().rstrip(TRAILING_PUNCT)
        start, end = match.start(), match.start() + len(candidate)
        if any(s <= start < e for s, e, _ in spans):
            continue
        spans.append((start, end, max(_weigh(candidate), URL_WEIGHT)))
    return sorted(spans)


def weighted_len(text: str) -> int:
    """X's weighted length of ``text``: NFC, URLs 23 each (a bare domain at
    least 23), then the per-code-point weights with emoji sequences as 2."""
    text = unicodedata.normalize("NFC", text)
    total, pos = 0, 0
    for start, end, weight in _url_spans(text):
        total += _weigh(text[pos:start]) + weight
        pos = end
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
