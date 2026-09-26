import json
import os

import pytest

from social import cli, config


def _post_args(*extra):
    return ["post", "--to", "bluesky", "--to", "linkedin", "--text", "Shipped 1.0: https://www.radiusred.uk/blog/", "--link", "https://www.radiusred.uk/blog/", "--title", "1.0", *extra]


def test_dry_run_prints_both_requests_and_touches_no_network(env_file, refusing_transport, capsys):
    rc = cli.main(["--env-file", str(env_file), *_post_args("--dry-run")], transport=refusing_transport, environ={})
    assert rc == 0
    out = capsys.readouterr().out
    docs = [json.loads(chunk) for chunk in out.replace("}\n{", "}\n\x00{").split("\x00")]
    assert [d["network"] for d in docs] == ["bluesky", "linkedin"]
    bsky, li = docs
    assert bsky["request"]["url"].endswith("com.atproto.repo.createRecord")
    assert bsky["request"]["body"]["record"]["embed"]["external"]["title"] == "1.0"
    assert li["request"]["url"] == "https://api.linkedin.com/rest/posts"
    assert li["request"]["body"]["author"] == "urn:li:organization:42"
    assert "Authorization" not in out and "app-pass" not in out


def test_dry_run_needs_no_credentials_at_all(tmp_path, refusing_transport, capsys):
    rc = cli.main(["--env-file", str(tmp_path / "none.env"), *_post_args("--dry-run")], transport=refusing_transport, environ={})
    assert rc == 0
    assert "urn:li:organization:<id>" in capsys.readouterr().out


def test_post_publishes_to_both_and_prints_urls(env_file, transport, capsys):
    transport.expect("POST", "createSession", body={"did": "did:plc:abc", "accessJwt": "jwt", "handle": "example.bsky.social"})
    transport.expect("POST", "createRecord", body={"uri": "at://did:plc:abc/app.bsky.feed.post/3k", "cid": "c"})
    transport.expect("POST", "/rest/posts", status=201, headers={"x-restli-id": "urn:li:share:9"})
    rc = cli.main(["--env-file", str(env_file), *_post_args()], transport=transport, environ={})
    assert rc == 0
    lines = [json.loads(l) for l in capsys.readouterr().out.splitlines()]
    assert lines[0]["url"] == "https://bsky.app/profile/example.bsky.social/post/3k"
    assert lines[1]["url"] == "https://www.linkedin.com/feed/update/urn:li:share:9/"
    # the access token was fresh (far-future expiry), so no refresh happened
    assert not any("oauth" in c["url"] for c in transport.calls)


def test_per_network_text_override(env_file, refusing_transport, tmp_path, capsys):
    short = tmp_path / "short.txt"
    short.write_text("short for bluesky")
    rc = cli.main(["--env-file", str(env_file), "post", "--to", "bluesky", "--to", "linkedin", "--text", "long form", "--bluesky-text-file", str(short), "--dry-run"], transport=refusing_transport, environ={})
    assert rc == 0
    out = capsys.readouterr().out
    assert '"text": "short for bluesky"' in out and '"commentary": "long form"' in out


def test_expired_token_is_refreshed_and_persisted_before_posting(env_file, transport, capsys):
    env_file.write_text(env_file.read_text().replace("LINKEDIN_ACCESS_TOKEN_EXPIRES_AT=9999999999", "LINKEDIN_ACCESS_TOKEN_EXPIRES_AT=1000"))
    transport.expect("POST", "oauth/v2/accessToken", body={"access_token": "fresh", "expires_in": 5183999, "refresh_token": "fresh-r", "refresh_token_expires_in": 22326553})
    transport.expect("POST", "/rest/posts", status=201, headers={"x-restli-id": "urn:li:share:1"})
    rc = cli.main(["--env-file", str(env_file), "post", "--to", "linkedin", "--text", "hi"], transport=transport, environ={})
    assert rc == 0
    assert transport.calls[1]["headers"]["Authorization"] == "Bearer fresh"
    text = env_file.read_text()
    assert "LINKEDIN_ACCESS_TOKEN=fresh\n" in text and "LINKEDIN_REFRESH_TOKEN=fresh-r\n" in text
    assert "refreshed" in capsys.readouterr().err


def test_unknown_expiry_is_learned_by_introspection(env_file, transport):
    env_file.write_text(env_file.read_text().replace("LINKEDIN_ACCESS_TOKEN_EXPIRES_AT=9999999999\n", ""))
    transport.expect("POST", "introspectToken", body={"active": True, "status": "active", "expires_at": 9999999999})
    transport.expect("POST", "/rest/posts", status=201, headers={"x-restli-id": "urn:li:share:2"})
    rc = cli.main(["--env-file", str(env_file), "post", "--to", "linkedin", "--text", "hi"], transport=transport, environ={})
    assert rc == 0
    assert [c["url"].rsplit("/", 1)[-1] for c in transport.calls] == ["introspectToken", "posts"]


def test_missing_credential_is_a_usage_error(tmp_path, refusing_transport, capsys):
    rc = cli.main(["--env-file", str(tmp_path / "none.env"), "post", "--to", "bluesky", "--text", "hi"], transport=refusing_transport, environ={})
    assert rc == 2
    assert "BSKY_HANDLE is not set" in capsys.readouterr().err


def test_api_failure_is_reported_per_network_and_nonzero(env_file, transport, capsys):
    transport.expect("POST", "createSession", status=401, body={"error": "AuthenticationRequired"})
    transport.expect("POST", "/rest/posts", status=201, headers={"x-restli-id": "urn:li:share:3"})
    rc = cli.main(["--env-file", str(env_file), *_post_args()], transport=transport, environ={})
    assert rc == 1
    lines = [json.loads(l) for l in capsys.readouterr().out.splitlines()]
    assert "HTTP 401" in lines[0]["error"] and lines[1]["urn"] == "urn:li:share:3"


def test_check_reports_both_networks_and_the_administered_page(env_file, transport, capsys):
    transport.expect("POST", "createSession", body={"did": "did:plc:abc", "accessJwt": "jwt", "handle": "example.bsky.social"})
    transport.expect("POST", "introspectToken", body={"active": True, "status": "active", "expires_at": 1798761600, "scope": "a,b"})
    transport.expect("GET", "organizationAcls", body={"elements": [{"organization": "urn:li:organization:42"}]})
    transport.expect("GET", "organizations/42", body={"localizedName": "Radius Red", "vanityName": "radiusred"})
    rc = cli.main(["--env-file", str(env_file), "check"], transport=transport, environ={})
    out = capsys.readouterr().out
    assert rc == 0
    assert "bluesky: ok — example.bsky.social (did:plc:abc)" in out
    assert "linkedin: token active, expires 2027-01-01; scopes: a b" in out
    assert "administers urn:li:organization:42 — Radius Red / radiusred (configured)" in out


def test_env_sourced_token_keeps_its_expiry_out_of_the_file_so_the_next_run_refreshes(env_file, transport, capsys):
    # Run 1: the orchestrator injects a (dead) access token; the file's token is stale too.
    env_file.write_text(env_file.read_text().replace("LINKEDIN_ACCESS_TOKEN_EXPIRES_AT=9999999999\n", ""))
    transport.expect("POST", "introspectToken", body={"active": False, "status": "expired"})
    transport.expect("POST", "oauth/v2/accessToken", body={"access_token": "fresh-1", "expires_in": 5183999, "refresh_token": "r-1", "refresh_token_expires_in": 100})
    transport.expect("POST", "/rest/posts", status=201, headers={"x-restli-id": "urn:li:share:1"})
    rc = cli.main(["--env-file", str(env_file), "post", "--to", "linkedin", "--text", "hi"], transport=transport, environ={"LINKEDIN_ACCESS_TOKEN": "injected-dead"})
    assert rc == 0
    text = env_file.read_text()
    assert "LINKEDIN_ACCESS_TOKEN=old-access\n" in text  # env value never written
    assert "LINKEDIN_ACCESS_TOKEN_EXPIRES_AT" not in text  # and no expiry beside the stale token
    assert "LINKEDIN_REFRESH_TOKEN=r-1\n" in text and "LINKEDIN_REFRESH_TOKEN_EXPIRES_AT=" in text
    assert "NOT persisted for LINKEDIN_ACCESS_TOKEN" in capsys.readouterr().err
    # Run 2, same file, same injected token: must introspect and refresh again, not trust a phantom expiry.
    transport.expect("POST", "introspectToken", body={"active": False, "status": "expired"})
    transport.expect("POST", "oauth/v2/accessToken", body={"access_token": "fresh-2", "expires_in": 5183999, "refresh_token": "r-2", "refresh_token_expires_in": 100})
    transport.expect("POST", "/rest/posts", status=201, headers={"x-restli-id": "urn:li:share:2"})
    rc = cli.main(["--env-file", str(env_file), "post", "--to", "linkedin", "--text", "hi"], transport=transport, environ={"LINKEDIN_ACCESS_TOKEN": "injected-dead"})
    assert rc == 0
    assert transport.calls[-1]["headers"]["Authorization"] == "Bearer fresh-2"


def test_parse_callback_handles_urls_and_bare_codes():
    assert cli.parse_callback("http://localhost:8765/callback?code=abc&state=s1") == ("abc", "s1")
    assert cli.parse_callback("/callback?code=abc") == ("abc", None)
    assert cli.parse_callback("rawcode") == ("rawcode", None)
    assert cli.parse_callback("") == (None, None)


def test_pasted_callback_with_wrong_state_is_refused(env_file, refusing_transport, monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "http://localhost:8765/callback?code=abc&state=forged")
    rc = cli.main(["--env-file", str(env_file), "auth", "linkedin", "--paste"], transport=refusing_transport, environ={})
    assert rc == 1
    assert "state mismatch" in capsys.readouterr().out


def test_comment_dry_run_prints_the_request_and_touches_no_network(env_file, refusing_transport, capsys):
    rc = cli.main(
        ["--env-file", str(env_file), "comment", "--urn", "urn:li:share:99",
         "--text", "Links: https://x.example/p", "--dry-run"],
        transport=refusing_transport, environ={},
    )
    assert rc == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["network"] == "linkedin" and doc["dry_run"] is True
    assert doc["request"]["url"] == "https://api.linkedin.com/rest/socialActions/urn%3Ali%3Ashare%3A99/comments"
    assert doc["request"]["body"]["message"]["text"] == "Links: https://x.example/p"
    assert doc["request"]["body"]["actor"] == "urn:li:organization:42"


def test_comment_publishes_and_prints_the_comment_urn(env_file, transport, capsys):
    transport.expect("POST", "/rest/socialActions/", status=201, headers={"x-restli-id": "urn:li:comment:(urn:li:share:99,1)"})
    rc = cli.main(
        ["--env-file", str(env_file), "comment", "--urn", "urn:li:share:99", "--text", "https://x.example/p"],
        transport=transport, environ={},
    )
    assert rc == 0
    assert json.loads(capsys.readouterr().out) == {
        "network": "linkedin", "urn": "urn:li:comment:(urn:li:share:99,1)", "object": "urn:li:share:99",
    }


# --- the default path and the transitional fallback (www#70, M7-R5) ---------


@pytest.fixture
def default_paths(tmp_path, monkeypatch):
    new = tmp_path / "radiusred" / "social.env"
    old = tmp_path / "codecrew" / "social.env"
    monkeypatch.setattr(config, "DEFAULT_ENV_FILE", new)
    monkeypatch.setattr(config, "LEGACY_ENV_FILE", old)
    return new, old


def test_no_env_file_flag_reads_the_new_default_path(default_paths, env_file, refusing_transport, capsys):
    new, _ = default_paths
    new.parent.mkdir(mode=0o700)
    new.write_text(env_file.read_text())
    rc = cli.main(_post_args("--dry-run"), transport=refusing_transport, environ={})
    assert rc == 0
    out, err = capsys.readouterr()
    assert '"author": "urn:li:organization:42"' in out
    assert err == ""


def test_legacy_path_is_read_with_one_hint_per_invocation(default_paths, env_file, refusing_transport, capsys):
    new, old = default_paths
    old.parent.mkdir(mode=0o700)
    old.write_text(env_file.read_text())
    rc = cli.main(_post_args("--dry-run"), transport=refusing_transport, environ={})
    assert rc == 0
    out, err = capsys.readouterr()
    assert '"author": "urn:li:organization:42"' in out
    assert err.count("\n") == 1 and str(old) in err and str(new) in err
    assert not new.exists()  # a dry run writes nothing anywhere


def test_neither_default_present_names_the_new_path_in_the_error(default_paths, refusing_transport, capsys):
    new, old = default_paths
    rc = cli.main(["post", "--to", "bluesky", "--text", "hi"], transport=refusing_transport, environ={})
    assert rc == 2
    err = capsys.readouterr().err
    assert f"BSKY_HANDLE is not set in the environment or {new}" in err and str(old) not in err


def test_rotation_from_the_legacy_file_persists_the_whole_set_to_the_new_path(default_paths, env_file, transport, capsys):
    new, old = default_paths
    old.parent.mkdir(mode=0o700)
    legacy_text = env_file.read_text().replace("LINKEDIN_ACCESS_TOKEN_EXPIRES_AT=9999999999", "LINKEDIN_ACCESS_TOKEN_EXPIRES_AT=1000")
    old.write_text(legacy_text)
    transport.expect("POST", "oauth/v2/accessToken", body={"access_token": "fresh", "expires_in": 5183999, "refresh_token": "fresh-r", "refresh_token_expires_in": 22326553})
    transport.expect("POST", "/rest/posts", status=201, headers={"x-restli-id": "urn:li:share:1"})
    rc = cli.main(["post", "--to", "linkedin", "--text", "hi"], transport=transport, environ={})
    assert rc == 0
    text = new.read_text()
    for line in ("# test creds\n", "BSKY_HANDLE=example.bsky.social\n", "BSKY_APP_PASSWORD=app-pass\n",
                 "LINKEDIN_CLIENT_ID=cid\n", "LINKEDIN_ORG_URN=urn:li:organization:42\n",
                 "LINKEDIN_ACCESS_TOKEN=fresh\n", "LINKEDIN_REFRESH_TOKEN=fresh-r\n"):
        assert line in text
    assert "old-access" not in text and "LINKEDIN_ACCESS_TOKEN_EXPIRES_AT=1000" not in text
    assert old.read_text() == legacy_text  # untouched
    assert oct(os.stat(new).st_mode & 0o777) == "0o600"
    assert oct(os.stat(new.parent).st_mode & 0o777) == "0o700"
    err = capsys.readouterr().err
    assert str(old) in err and "refreshed" in err
    # the next run finds the new file and reads it without the hint
    transport.expect("POST", "/rest/posts", status=201, headers={"x-restli-id": "urn:li:share:2"})
    rc = cli.main(["post", "--to", "linkedin", "--text", "hi"], transport=transport, environ={})
    assert rc == 0
    assert transport.calls[-1]["headers"]["Authorization"] == "Bearer fresh"
    assert str(old) not in capsys.readouterr().err


def test_explicit_env_file_ignores_the_legacy_file(default_paths, env_file, tmp_path, refusing_transport, capsys):
    _, old = default_paths
    old.parent.mkdir(mode=0o700)
    old.write_text(env_file.read_text())
    rc = cli.main(["--env-file", str(tmp_path / "none.env"), "post", "--to", "bluesky", "--text", "hi"], transport=refusing_transport, environ={})
    assert rc == 2
    err = capsys.readouterr().err
    assert "none.env" in err and str(old) not in err


def test_env_file_help_names_the_new_default():
    assert "~/.config/radiusred/social.env" in cli.build_parser().format_help()
