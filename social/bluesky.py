"""Bluesky: app-password session, then one ``app.bsky.feed.post`` record."""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone

from .transport import ApiError, Response

DEFAULT_PDS = "https://bsky.social"
MAX_GRAPHEMES = 300
URL_RE = re.compile(r"https?://[^\s<>()\[\]\"']+")
# A tag is "#" plus word characters, not glued to a preceding word character
# (so a URL fragment or "a#b" is not a tag) and not purely numeric.
TAG_RE = re.compile(r"(?<!\w)#(\w+)")
TRAILING_PUNCT = ".,;:!?'\")"


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


def facets(text: str) -> list[dict]:
    """All facets (links, tags), in byte order."""
    return sorted(link_facets(text) + tag_facets(text), key=lambda f: f["index"]["byteStart"])


def build_post(
    text: str,
    link: str | None = None,
    title: str | None = None,
    description: str | None = None,
    created_at: datetime | None = None,
) -> dict:
    text = text.strip()
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
    found = facets(text)
    if found:
        record["facets"] = found
    if link:
        record["embed"] = {
            "$type": "app.bsky.embed.external",
            "external": {"uri": link, "title": title or link, "description": description or ""},
        }
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
