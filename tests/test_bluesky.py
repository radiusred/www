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


def test_tag_facets_cover_hashtags_with_byte_offsets_and_strip_the_hash():
    text = "Shipped #CodeCrew 1.0 — #agentic #OpenSource"
    tags = bluesky.tag_facets(text)
    assert [f["features"][0] for f in tags] == [
        {"$type": "app.bsky.richtext.facet#tag", "tag": "CodeCrew"},
        {"$type": "app.bsky.richtext.facet#tag", "tag": "agentic"},
        {"$type": "app.bsky.richtext.facet#tag", "tag": "OpenSource"},
    ]
    start = len("Shipped #CodeCrew 1.0 — ".encode())
    assert tags[1]["index"] == {"byteStart": start, "byteEnd": start + len("#agentic")}
    assert text.encode()[tags[2]["index"]["byteStart"] : tags[2]["index"]["byteEnd"]] == b"#OpenSource"


def test_tag_facets_skip_url_fragments_numbers_and_glued_hashes():
    text = "issue#45 https://x.example/p#section #1 #2026 #real"
    assert [f["features"][0]["tag"] for f in bluesky.tag_facets(text)] == ["real"]


def test_build_post_merges_link_and_tag_facets_in_byte_order():
    record = bluesky.build_post("#first https://a.example/ #last", created_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    kinds = [(f["index"]["byteStart"], f["features"][0]["$type"].rsplit("#", 1)[-1]) for f in record["facets"]]
    assert kinds == [(0, "tag"), (7, "link"), (7 + len("https://a.example/ "), "tag")]


def test_markdown_links_become_display_text_with_a_link_facet():
    text, found = bluesky.facets("Read [the 1.0 article](https://x.example/a-very-long-path) and #tag it")
    assert text == "Read the 1.0 article and #tag it"
    link, tag = found
    start = len("Read ".encode())
    assert link["index"] == {"byteStart": start, "byteEnd": start + len("the 1.0 article")}
    assert link["features"][0]["uri"] == "https://x.example/a-very-long-path"
    assert tag["features"][0]["tag"] == "tag"
    assert text.encode()[tag["index"]["byteStart"] : tag["index"]["byteEnd"]] == b"#tag"


def test_markdown_links_after_non_ascii_and_beside_bare_urls():
    text, found = bluesky.facets("café [one](https://a.example/1) https://b.example/2 [two](https://c.example/3)")
    assert text == "café one https://b.example/2 two"
    assert [f["features"][0]["uri"] for f in found] == ["https://a.example/1", "https://b.example/2", "https://c.example/3"]
    for f in found:
        span = text.encode()[f["index"]["byteStart"] : f["index"]["byteEnd"]].decode()
        assert span in ("one", "https://b.example/2", "two")


def test_grapheme_limit_counts_the_display_text_not_the_url():
    long_url = "https://x.example/" + "p" * 400
    record = bluesky.build_post(f"[short]({long_url})", created_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert record["text"] == "short"
    assert record["facets"][0]["features"][0]["uri"] == long_url
