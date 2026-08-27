import urllib.parse

import pytest

from social import linkedin
from social.transport import ApiError


def test_escape_commentary_escapes_every_reserved_character():
    assert linkedin.escape_commentary("a (b) [c] {d} <e> *f* _g_ ~h~ #i @j |k| \\") == (
        "a \\(b\\) \\[c\\] \\{d\\} \\<e\\> \\*f\\* \\_g\\_ \\~h\\~ {hashtag|\\#|i} \\@j \\|k\\| \\\\"
    )
    assert linkedin.escape_commentary("plain, text. 1.0 — fine!") == "plain, text. 1.0 — fine!"


def test_build_post_shape_with_article():
    body = linkedin.build_post("urn:li:organization:42", "Read (this)", link="https://x.example/p", title="T", description="D")
    assert body["author"] == "urn:li:organization:42"
    assert body["commentary"] == "Read \\(this\\)"
    assert body["visibility"] == "PUBLIC"
    assert body["lifecycleState"] == "PUBLISHED"
    assert body["distribution"]["feedDistribution"] == "MAIN_FEED"
    assert body["content"] == {"article": {"source": "https://x.example/p", "title": "T", "description": "D"}}


def test_build_post_without_link_has_no_content():
    body = linkedin.build_post("urn:li:organization:42", "text")
    assert "content" not in body
    with pytest.raises(ValueError, match="empty"):
        linkedin.build_post("urn:li:organization:42", " ")


def test_post_sends_versioned_headers_and_reads_the_urn_header(transport):
    transport.expect("POST", "/rest/posts", status=201, headers={"x-restli-id": "urn:li:share:99"})
    client = linkedin.LinkedIn(transport, "cid", "csecret", "tok", version="202608")
    result = client.post(linkedin.build_post("urn:li:organization:42", "hi"))
    assert result == {"urn": "urn:li:share:99", "url": "https://www.linkedin.com/feed/update/urn:li:share:99/"}
    headers = transport.calls[0]["headers"]
    assert headers["Authorization"] == "Bearer tok"
    assert headers["LinkedIn-Version"] == "202608"
    assert headers["X-Restli-Protocol-Version"] == "2.0.0"


def test_retired_version_surfaces_as_api_error(transport):
    transport.expect("POST", "/rest/posts", status=426, body={"code": "NONEXISTENT_VERSION", "message": "Requested version 20250801 is not active"})
    client = linkedin.LinkedIn(transport, "cid", "csecret", "tok", version="202508")
    with pytest.raises(ApiError, match="HTTP 426 .*NONEXISTENT_VERSION"):
        client.post(linkedin.build_post("urn:li:organization:42", "hi"))


def test_refresh_posts_a_form_and_adopts_the_new_token(transport):
    transport.expect("POST", "oauth/v2/accessToken", body={"access_token": "new", "expires_in": 5183999, "refresh_token": "new-r", "refresh_token_expires_in": 100, "scope": "w_organization_social"})
    client = linkedin.LinkedIn(transport, "cid", "csecret", "old")
    tokens = client.refresh("old-r")
    assert tokens["access_token"] == "new" and client.access_token == "new"
    call = transport.calls[0]
    assert call["headers"]["Content-Type"] == "application/x-www-form-urlencoded"
    assert urllib.parse.parse_qs(call["body"].decode()) == {
        "grant_type": ["refresh_token"], "refresh_token": ["old-r"], "client_id": ["cid"], "client_secret": ["csecret"],
    }


def test_auth_url_carries_scopes_state_and_redirect():
    client = linkedin.LinkedIn(None, "cid", "csecret")
    url, state = client.auth_url("http://localhost:8765/callback", ("a", "b"), state="s1")
    parsed = urllib.parse.urlparse(url)
    assert parsed.netloc == "www.linkedin.com" and parsed.path == "/oauth/v2/authorization"
    query = urllib.parse.parse_qs(parsed.query)
    assert query == {"response_type": ["code"], "client_id": ["cid"], "redirect_uri": ["http://localhost:8765/callback"], "state": ["s1"], "scope": ["a b"]}
    assert state == "s1"


def test_organization_acls_and_lookup(transport):
    transport.expect("GET", "organizationAcls", body={"elements": [{"organization": "urn:li:organization:42", "role": "ADMINISTRATOR", "state": "APPROVED"}]})
    transport.expect("GET", "organizations/42", body={"id": 42, "vanityName": "radiusred", "localizedName": "Radius Red"})
    client = linkedin.LinkedIn(transport, "cid", "csecret", "tok")
    (acl,) = client.organization_acls()
    assert client.organization(acl["organization"])["vanityName"] == "radiusred"


def test_escape_commentary_renders_hashtags_as_entities_and_leaves_urls_alone():
    text = "Ship (it) #CodeCrew https://x.example/p_1#frag #2026 and #DevTools"
    assert linkedin.escape_commentary(text) == (
        "Ship \\(it\\) {hashtag|\\#|CodeCrew} https://x.example/p_1#frag \\#2026 and {hashtag|\\#|DevTools}"
    )
