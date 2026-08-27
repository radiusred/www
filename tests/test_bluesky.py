from datetime import datetime, timezone

import pytest

from social import bluesky
from social.transport import ApiError


def test_link_facets_use_utf8_byte_offsets():
    text = "café → https://www.radiusred.uk/blog/, then more"
    (facet,) = bluesky.link_facets(text)
    start = len("café → ".encode())
    assert facet["index"] == {"byteStart": start, "byteEnd": start + len("https://www.radiusred.uk/blog/")}
    assert facet["features"] == [{"$type": "app.bsky.richtext.facet#link", "uri": "https://www.radiusred.uk/blog/"}]


def test_link_facets_trim_trailing_punctuation_and_find_several():
    text = "See https://a.example/x. Also (https://b.example/y)!"
    uris = [f["features"][0]["uri"] for f in bluesky.link_facets(text)]
    assert uris == ["https://a.example/x", "https://b.example/y"]


def test_build_post_shape_with_link_card():
    when = datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc)
    record = bluesky.build_post("Hello https://x.example/p", link="https://x.example/p", title="T", description="D", created_at=when)
    assert record["$type"] == "app.bsky.feed.post"
    assert record["createdAt"] == "2026-08-27T12:00:00.000Z"
    assert record["facets"][0]["features"][0]["uri"] == "https://x.example/p"
    assert record["embed"] == {
        "$type": "app.bsky.embed.external",
        "external": {"uri": "https://x.example/p", "title": "T", "description": "D"},
    }


def test_build_post_without_links_has_no_facets_or_embed():
    record = bluesky.build_post("plain text", created_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert "facets" not in record and "embed" not in record


def test_build_post_enforces_the_grapheme_limit():
    ok = "é" * 300 + "́" * 5  # combining marks do not count
    assert bluesky.grapheme_len(ok) == 300
    bluesky.build_post(ok)
    with pytest.raises(ValueError, match="301 graphemes"):
        bluesky.build_post("a" * 301)
    with pytest.raises(ValueError, match="empty"):
        bluesky.build_post("   ")


def test_post_logs_in_then_creates_record_and_returns_url(transport):
    transport.expect("POST", "createSession", body={"did": "did:plc:abc", "accessJwt": "jwt", "handle": "example.bsky.social"})
    transport.expect("POST", "createRecord", body={"uri": "at://did:plc:abc/app.bsky.feed.post/3kxyz", "cid": "bafy"})
    client = bluesky.Bluesky(transport, "example.bsky.social", "app-pass")
    record = bluesky.build_post("hi", created_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    result = client.post(record)
    assert result["url"] == "https://bsky.app/profile/example.bsky.social/post/3kxyz"
    login, create = transport.bodies()
    assert login == {"identifier": "example.bsky.social", "password": "app-pass"}
    assert create == {"repo": "did:plc:abc", "collection": "app.bsky.feed.post", "record": record}
    assert transport.calls[1]["headers"]["Authorization"] == "Bearer jwt"


def test_failed_login_raises_api_error_with_body(transport):
    transport.expect("POST", "createSession", status=401, body={"error": "AuthenticationRequired", "message": "Invalid identifier or password"})
    client = bluesky.Bluesky(transport, "example.bsky.social", "wrong")
    with pytest.raises(ApiError, match="HTTP 401 .*Invalid identifier"):
        client.login()
