"""Bluesky: app-password session, then one ``app.bsky.feed.post`` record —
a top-level post, or a reply with ``root`` and ``parent`` strong refs."""

from __future__ import annotations

import json
import re
import unicodedata
import urllib.parse
from datetime import datetime, timezone

from .transport import ApiError, Response

DEFAULT_PDS = "https://bsky.social"
MAX_GRAPHEMES = 300
URL_RE = re.compile(r"https?://[^\s<>()\[\]\"']+")
# [label](https://…) — the label is what readers see; the facet carries the URL.
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")
# A tag is "#" plus word characters, not glued to a preceding word character
# (so a URL fragment or "a#b" is not a tag) and not purely numeric.
TAG_RE = re.compile(r"(?<!\w)#(\w+)")
TRAILING_PUNCT = ".,;:!?'\")"
POST_COLLECTION = "app.bsky.feed.post"
# at://<did>/app.bsky.feed.post/<rkey>, or the web client's URL for the same post.
AT_URI_RE = re.compile(r"^at://(?P<repo>[^/]+)/app\.bsky\.feed\.post/(?P<rkey>[^/?#]+)$")
POST_URL_RE = re.compile(r"^https?://(?:www\.)?bsky\.app/profile/(?P<repo>[^/]+)/post/(?P<rkey>[^/?#]+)(?:[/?#].*)?$")


def grapheme_len(text: str) -> int:
    """Close enough to Bluesky's count for a length guard: combining marks and
    zero-width joiners extend the previous grapheme instead of adding one."""
    return sum(1 for ch in text if not unicodedata.combining(ch) and ch != "‍")


def _facet(text: str, start: int, span: str, feature: dict) -> dict:
    byte_start = len(text[:start].encode("utf-8"))
    return {
        "index": {"byteStart": byte_start, "byteEnd": byte_start + len(span.encode("utf-8"))},
        "features": [feature],
    }


def link_facets(text: str) -> list[dict]:
    """Rich-text facets for every URL in ``text``, with UTF-8 *byte* offsets —
    the protocol's unit, not characters."""
    facets = []
    for match in URL_RE.finditer(text):
        url = match.group().rstrip(TRAILING_PUNCT)
        facets.append(_facet(text, match.start(), url, {"$type": "app.bsky.richtext.facet#link", "uri": url}))
    return facets


def tag_facets(text: str) -> list[dict]:
    """Facets for every ``#hashtag`` — without them a tag is plain text and
    the post reaches nobody who follows the tag. URL fragments are skipped."""
    url_spans = [(m.start(), m.end()) for m in URL_RE.finditer(text)]
    facets = []
    for match in TAG_RE.finditer(text):
        tag = match.group(1)
        if tag.isdigit() or any(s <= match.start() < e for s, e in url_spans):
            continue
        facets.append(_facet(text, match.start(), match.group(), {"$type": "app.bsky.richtext.facet#tag", "tag": tag}))
    return facets


def resolve_markdown_links(text: str) -> tuple[str, list[dict]]:
    """Replace ``[label](url)`` with ``label`` and return the text plus a link
    facet per label, with byte offsets into the *replaced* text."""
    out, facets, pos = [], [], 0
    consumed = ""
    for match in MD_LINK_RE.finditer(text):
        consumed += text[pos : match.start()]
        label, url = match.group(1), match.group(2)
        facets.append(_facet(consumed + label, len(consumed), label, {"$type": "app.bsky.richtext.facet#link", "uri": url}))
        consumed += label
        pos = match.end()
    consumed += text[pos:]
    return consumed, facets


def facets(text: str) -> tuple[str, list[dict]]:
    """The display text and all its facets (labelled links, bare links, tags),
    in byte order."""
    text, labelled = resolve_markdown_links(text)
    found = labelled + link_facets(text) + tag_facets(text)
    return text, sorted(found, key=lambda f: f["index"]["byteStart"])


def parse_post_ref(ref: str) -> tuple[str, str]:
    """``(repo, rkey)`` from an ``at://`` post URI or a ``bsky.app`` post URL.
    The repo is a DID in the URI, a handle or a DID in the URL."""
    ref = ref.strip()
    match = AT_URI_RE.match(ref) or POST_URL_RE.match(ref)
    if not match:
        raise ValueError(f"{ref!r} is not a Bluesky post at:// URI or bsky.app post URL")
    return match.group("repo"), match.group("rkey")


def post_uri(did: str, rkey: str) -> str:
    return f"at://{did}/{POST_COLLECTION}/{rkey}"


def build_post(
    text: str,
    link: str | None = None,
    title: str | None = None,
    description: str | None = None,
    created_at: datetime | None = None,
    reply: dict | None = None,
) -> dict:
    text, found = facets(text.strip())
    if not text:
        raise ValueError("post text is empty")
    count = grapheme_len(text)
    if count > MAX_GRAPHEMES:
        raise ValueError(f"post is {count} graphemes; Bluesky allows {MAX_GRAPHEMES}")
    when = created_at or datetime.now(timezone.utc)
    record = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": when.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
    }
    if found:
        record["facets"] = found
    if link:
        record["embed"] = {
            "$type": "app.bsky.embed.external",
            "external": {"uri": link, "title": title or link, "description": description or ""},
        }
    if reply:
        record["reply"] = reply
    return record


class Bluesky:
    def __init__(self, transport, handle: str, app_password: str, pds: str = DEFAULT_PDS):
        self.transport = transport
        self.handle = handle
        self.app_password = app_password
        self.pds = pds.rstrip("/")
        self.session: dict | None = None

    def _xrpc(self, method: str, body: dict, token: str | None = None) -> Response:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return self.transport("POST", f"{self.pds}/xrpc/{method}", headers, json.dumps(body).encode())

    def _query(self, what: str, method: str, params: dict[str, str], token: str | None = None) -> dict:
        """A GET on the PDS; with the session token it proxies ``app.bsky.*``
        reads to the appview, so any post on the network can be looked up."""
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        resp = self.transport("GET", f"{self.pds}/xrpc/{method}?{urllib.parse.urlencode(params)}", headers, None)
        if not resp.ok:
            raise ApiError(what, resp)
        return resp.json()

    def resolve_handle(self, handle: str) -> str:
        if handle.startswith("did:"):
            return handle
        return self._query("Bluesky handle lookup failed", "com.atproto.identity.resolveHandle", {"handle": handle})["did"]

    def get_post(self, uri: str) -> dict:
        """The post at ``uri`` as the appview has it: ``uri``, ``cid`` and its
        ``record``. Needs a session."""
        session = self.session or self.login()
        posts = self._query("Bluesky post lookup failed", "app.bsky.feed.getPosts", {"uris": uri}, session["accessJwt"]).get("posts") or []
        if not posts:
            raise ValueError(f"no post at {uri}")
        return posts[0]

    def reply_refs(self, ref: str) -> dict:
        """``{"root", "parent"}`` strong refs for a reply to the post ``ref``
        names: the parent is that post; the root is the thread it is in —
        the parent's own root when it is itself a reply, else the parent."""
        repo, rkey = parse_post_ref(ref)
        uri = post_uri(self.resolve_handle(repo), rkey)
        post = self.get_post(uri)
        parent = {"uri": post["uri"], "cid": post["cid"]}
        root = (post.get("record") or {}).get("reply", {}).get("root") or parent
        return {"root": {"uri": root["uri"], "cid": root["cid"]}, "parent": parent}

    def login(self) -> dict:
        resp = self._xrpc(
            "com.atproto.server.createSession",
            {"identifier": self.handle, "password": self.app_password},
        )
        if not resp.ok:
            raise ApiError("Bluesky login failed", resp)
        self.session = resp.json()
        return self.session

    def create_record_request(self, record: dict, did: str = "<did>") -> dict:
        return {
            "method": "POST",
            "url": f"{self.pds}/xrpc/com.atproto.repo.createRecord",
            "body": {"repo": did, "collection": "app.bsky.feed.post", "record": record},
        }

    def post(self, record: dict) -> dict:
        session = self.session or self.login()
        request = self.create_record_request(record, session["did"])
        resp = self._xrpc("com.atproto.repo.createRecord", request["body"], session["accessJwt"])
        if not resp.ok:
            raise ApiError("Bluesky createRecord failed", resp)
        data = resp.json()
        rkey = data["uri"].rsplit("/", 1)[-1]
        return {
            "uri": data["uri"],
            "cid": data.get("cid"),
            "url": f"https://bsky.app/profile/{session.get('handle', self.handle)}/post/{rkey}",
        }
