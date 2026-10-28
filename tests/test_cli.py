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
    transport.expect("GET", "/2/users/me", body={"data": {"id": "12", "username": "example_uk"}})
    rc = cli.main(["--env-file", str(env_file), "check"], transport=transport, environ={})
    out = capsys.readouterr().out
    assert rc == 0
    assert "bluesky: ok — example.bsky.social (did:plc:abc)" in out
    assert "linkedin: token active, expires 2027-01-01; scopes: a b" in out
    assert "administers urn:li:organization:42 — Radius Red / radiusred (configured)" in out
    assert "x: ok — @example_uk (12)" in out


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


# --- the X transport (www#71, M7-R1/R2/R3) -----------------------------------


def test_x_dry_run_prints_the_request_and_touches_no_network(env_file, refusing_transport, capsys):
    rc = cli.main(["--env-file", str(env_file), "post", "--to", "x", "--text", "Shipped 1.0 today.", "--dry-run"], transport=refusing_transport, environ={})
    assert rc == 0
    out, err = capsys.readouterr()
    doc = json.loads(out)
    assert doc == {"network": "x", "dry_run": True, "request": {"method": "POST", "url": "https://api.x.com/2/tweets", "body": {"text": "Shipped 1.0 today."}}}
    assert "Authorization" not in out and "xsecret" not in out and err == ""


def test_x_dry_run_needs_no_credentials(tmp_path, refusing_transport, capsys):
    rc = cli.main(["--env-file", str(tmp_path / "none.env"), "post", "--to", "x", "--text", "hi", "--dry-run"], transport=refusing_transport, environ={})
    assert rc == 0
    assert json.loads(capsys.readouterr().out)["request"]["body"] == {"text": "hi"}


def test_x_post_publishes_and_prints_the_url(env_file, transport, capsys):
    transport.expect("POST", "/2/tweets", status=201, body={"data": {"id": "1970", "text": "hi"}})
    rc = cli.main(["--env-file", str(env_file), "post", "--to", "x", "--text", "hi"], transport=transport, environ={})
    assert rc == 0
    assert json.loads(capsys.readouterr().out) == {"network": "x", "id": "1970", "url": "https://x.com/example_uk/status/1970"}
    assert transport.calls[0]["headers"]["Authorization"].startswith("OAuth ")
    assert not env_file.read_text().endswith(".tmp")  # nothing rotates, nothing is written


def test_x_post_alongside_the_other_networks_is_explicit_and_ordered(env_file, transport, capsys):
    transport.expect("POST", "createSession", body={"did": "did:plc:abc", "accessJwt": "jwt", "handle": "example.bsky.social"})
    transport.expect("POST", "createRecord", body={"uri": "at://did:plc:abc/app.bsky.feed.post/3k", "cid": "c"})
    transport.expect("POST", "/2/tweets", status=201, body={"data": {"id": "7"}})
    rc = cli.main(["--env-file", str(env_file), "post", "--to", "bluesky", "--to", "x", "--text", "hi"], transport=transport, environ={})
    assert rc == 0
    assert [json.loads(l)["network"] for l in capsys.readouterr().out.splitlines()] == ["bluesky", "x"]


def test_to_has_no_implicit_all(env_file, refusing_transport, capsys):
    with pytest.raises(SystemExit, match="--to x is required"):
        cli.main(["--env-file", str(env_file), "post", "--text", "hi"], transport=refusing_transport, environ={})
    with pytest.raises(SystemExit):
        cli.main(["--env-file", str(env_file), "post", "--to", "all", "--text", "hi"], transport=refusing_transport, environ={})


def test_x_over_length_text_is_refused_before_any_network_call(env_file, refusing_transport, capsys):
    text = "a" * 258 + " https://www.radiusred.uk/blog/"
    # --skip-lint: the URL in the body is the point here, and lint would refuse it first
    rc = cli.main(["--env-file", str(env_file), "post", "--to", "bluesky", "--to", "x", "--text", text, "--skip-lint"], transport=refusing_transport, environ={})
    assert rc == 2
    assert "error: post is 282 weighted characters; X allows 280 (every URL counts as 23)" in capsys.readouterr().err


def test_x_text_override_and_link_note(env_file, refusing_transport, tmp_path, capsys):
    short = tmp_path / "x.txt"
    short.write_text("for x https://www.radiusred.uk/\n")
    rc = cli.main(["--env-file", str(env_file), "post", "--to", "linkedin", "--to", "x", "--text", "long form", "--x-text-file", str(short), "--link", "https://www.radiusred.uk/", "--dry-run", "--skip-lint"], transport=refusing_transport, environ={})
    assert rc == 0
    out, err = capsys.readouterr()
    assert '"text": "for x https://www.radiusred.uk/"' in out and '"commentary": "long form"' in out
    assert "x: --link/--title/--description are not applied on X; the link goes in the reply" in err


def _check_bluesky_and_linkedin(transport):
    transport.expect("POST", "createSession", body={"did": "did:plc:abc", "accessJwt": "jwt", "handle": "example.bsky.social"})
    transport.expect("POST", "introspectToken", body={"active": True, "status": "active", "expires_at": 1798761600, "scope": "a,b"})
    transport.expect("GET", "organizationAcls", body={"elements": [{"organization": "urn:li:organization:42"}]})
    transport.expect("GET", "organizations/42", body={"localizedName": "Radius Red", "vanityName": "radiusred"})


def test_check_verifies_the_x_handle(env_file, transport, capsys):
    _check_bluesky_and_linkedin(transport)
    transport.expect("GET", "/2/users/me", body={"data": {"id": "12", "name": "Example", "username": "Example_UK"}})
    rc = cli.main(["--env-file", str(env_file), "check"], transport=transport, environ={})
    assert rc == 0
    assert "x: ok — @Example_UK (12)" in capsys.readouterr().out


def test_check_fails_when_the_tokens_belong_to_another_account(env_file, transport, capsys):
    _check_bluesky_and_linkedin(transport)
    transport.expect("GET", "/2/users/me", body={"data": {"id": "13", "username": "someone_else"}})
    rc = cli.main(["--env-file", str(env_file), "check"], transport=transport, environ={})
    assert rc == 1
    assert "x: FAILED — the tokens belong to @someone_else, not @example_uk (X_HANDLE)" in capsys.readouterr().out


def test_check_reports_out_of_credits_plainly(env_file, transport, capsys):
    _check_bluesky_and_linkedin(transport)
    transport.expect("GET", "/2/users/me", status=402, body={"detail": "credits depleted", "status": 402, "title": "Payment Required", "type": "https://api.x.com/2/problems/credits-depleted"})
    rc = cli.main(["--env-file", str(env_file), "check"], transport=transport, environ={})
    assert rc == 1
    out = capsys.readouterr().out
    assert "x: FAILED — X check failed: out of credits — " in out and "buy credits in the X Developer Console (https://console.x.com/)" in out


def test_post_reports_out_of_credits_plainly(env_file, transport, capsys):
    transport.expect("POST", "/2/tweets", status=402, body={"detail": "credits depleted", "status": 402, "title": "Payment Required", "type": "https://api.x.com/2/problems/credits-depleted"})
    rc = cli.main(["--env-file", str(env_file), "post", "--to", "x", "--text", "hi"], transport=transport, environ={})
    assert rc == 1
    doc = json.loads(capsys.readouterr().out)
    assert doc["network"] == "x" and doc["error"].startswith("X post failed: out of credits — ")


def test_check_without_x_keys_reports_the_missing_key(env_file, transport, capsys):
    env_file.write_text("\n".join(l for l in env_file.read_text().splitlines() if not l.startswith("X_")) + "\n")
    _check_bluesky_and_linkedin(transport)
    rc = cli.main(["--env-file", str(env_file), "check"], transport=transport, environ={})
    assert rc == 1
    assert "x: FAILED — X_HANDLE is not set" in capsys.readouterr().out


# --- two accounts (www#91, M10-R1) --------------------------------------------


def _bluesky_login(transport, handle="example.bsky.social", did="did:plc:abc"):
    transport.expect("POST", "createSession", body={"did": did, "accessJwt": "jwt", "handle": handle})


def test_account_is_a_global_option_defaulting_to_radiusred(env_file, transport, capsys):
    transport.expect("POST", "/2/tweets", status=201, body={"data": {"id": "1"}})
    rc = cli.main(["--env-file", str(env_file), "post", "--to", "x", "--text", "hi"], transport=transport, environ={})
    assert rc == 0
    assert json.loads(capsys.readouterr().out)["url"] == "https://x.com/example_uk/status/1"
    assert 'oauth_token="xtoken"' in transport.calls[0]["headers"]["Authorization"]
    with pytest.raises(SystemExit):  # after the verb it is not recognised
        cli.main(["--env-file", str(env_file), "post", "--account", "codecrew", "--to", "x", "--text", "hi"], transport=transport, environ={})
    with pytest.raises(SystemExit):
        cli.main(["--env-file", str(env_file), "--account", "nobody", "check"], transport=transport, environ={})


def test_codecrew_account_posts_with_the_codecrew_keys_under_the_shared_x_app(env_file, transport, capsys):
    _bluesky_login(transport, handle="crew.example", did="did:plc:crew")
    transport.expect("POST", "createRecord", body={"uri": "at://did:plc:crew/app.bsky.feed.post/3k", "cid": "c"})
    transport.expect("POST", "/2/tweets", status=201, body={"data": {"id": "2"}})
    rc = cli.main(["--env-file", str(env_file), "--account", "codecrew", "post", "--to", "bluesky", "--to", "x", "--text", "hi"], transport=transport, environ={})
    assert rc == 0
    lines = [json.loads(l) for l in capsys.readouterr().out.splitlines()]
    assert lines[0]["url"] == "https://bsky.app/profile/crew.example/post/3k"
    assert lines[1]["url"] == "https://x.com/crewworks/status/2"
    assert transport.bodies()[0] == {"identifier": "crew.example", "password": "crew-pass"}
    auth = transport.calls[2]["headers"]["Authorization"]
    assert 'oauth_token="crewtoken"' in auth and 'oauth_consumer_key="xkey"' in auth  # the account's token, the app's key


def test_codecrew_account_without_its_keys_names_the_prefixed_key(env_file, refusing_transport, capsys):
    env_file.write_text("\n".join(l for l in env_file.read_text().splitlines() if not l.startswith("CODECREW_")) + "\n")
    rc = cli.main(["--env-file", str(env_file), "--account", "codecrew", "post", "--to", "x", "--text", "hi"], transport=refusing_transport, environ={})
    assert rc == 2
    assert "error: CODECREW_X_HANDLE is not set" in capsys.readouterr().err


def test_codecrew_account_refuses_linkedin_before_any_network_call(env_file, refusing_transport, tmp_path):
    for argv in (
        ["post", "--to", "linkedin", "--text", "hi"],
        ["post", "--to", "bluesky", "--to", "linkedin", "--text", "hi"],
        ["post", "--to", "linkedin", "--text", "hi", "--dry-run"],
        ["comment", "--urn", "urn:li:share:1", "--text", "hi"],
        ["auth", "linkedin", "--paste"],
    ):
        with pytest.raises(SystemExit, match="LinkedIn posts as the Radius Red Page only; --account codecrew has no LinkedIn"):
            cli.main(["--env-file", str(env_file), "--account", "codecrew", *argv], transport=refusing_transport, environ={})


def test_check_codecrew_proves_both_handles_and_skips_linkedin(env_file, transport, capsys):
    _bluesky_login(transport, handle="crew.example", did="did:plc:crew")
    transport.expect("GET", "/2/users/me", body={"data": {"id": "77", "username": "CrewWorks"}})
    rc = cli.main(["--env-file", str(env_file), "--account", "codecrew", "check"], transport=transport, environ={})
    out = capsys.readouterr().out
    assert rc == 0
    assert "bluesky: ok — crew.example (did:plc:crew)" in out
    assert "linkedin: skipped — Radius Red's Page only; --account codecrew has no LinkedIn" in out
    assert "x: ok — @CrewWorks (77)" in out
    assert transport.bodies()[0]["identifier"] == "crew.example"
    assert 'oauth_token="crewtoken"' in transport.calls[1]["headers"]["Authorization"]
    assert not any("linkedin" in c["url"] for c in transport.calls)


def test_check_codecrew_fails_when_the_tokens_are_radius_reds(env_file, transport, capsys):
    _bluesky_login(transport, handle="example.bsky.social", did="did:plc:abc")  # Radius Red's session came back
    transport.expect("GET", "/2/users/me", body={"data": {"id": "12", "username": "example_uk"}})
    rc = cli.main(["--env-file", str(env_file), "--account", "codecrew", "check"], transport=transport, environ={})
    out = capsys.readouterr().out
    assert rc == 1
    assert "bluesky: FAILED — the session is example.bsky.social, not crew.example (CODECREW_BSKY_HANDLE)" in out
    assert "x: FAILED — the tokens belong to @example_uk, not @crewworks (CODECREW_X_HANDLE)" in out


def test_check_radiusred_still_compares_the_bluesky_handle(env_file, transport, capsys):
    _bluesky_login(transport, handle="someone.else", did="did:plc:zzz")
    transport.expect("POST", "introspectToken", body={"active": True, "status": "active", "expires_at": 1798761600, "scope": "a"})
    transport.expect("GET", "organizationAcls", body={"elements": [{"organization": "urn:li:organization:42"}]})
    transport.expect("GET", "organizations/42", body={"localizedName": "Radius Red", "vanityName": "radiusred"})
    transport.expect("GET", "/2/users/me", body={"data": {"id": "12", "username": "example_uk"}})
    rc = cli.main(["--env-file", str(env_file), "check"], transport=transport, environ={})
    assert rc == 1
    assert "bluesky: FAILED — the session is someone.else, not example.bsky.social (BSKY_HANDLE)" in capsys.readouterr().out


# --- auth x: the PIN flow for a second account (www#91, M10-R1) --------------


def _pin_flow(transport, screen_name="crewworks"):
    transport.expect("POST", "/oauth/request_token", body=b"oauth_token=reqtok&oauth_token_secret=reqsec&oauth_callback_confirmed=true")
    transport.expect("POST", "/oauth/access_token", body=f"oauth_token=newtok&oauth_token_secret=newsec&user_id=77&screen_name={screen_name}".encode())


def test_auth_x_mints_and_persists_the_accounts_tokens_without_printing_them(env_file, transport, monkeypatch, capsys):
    _pin_flow(transport)
    prompts = []
    monkeypatch.setattr("builtins.input", lambda prompt: prompts.append(prompt) or "7654321")
    rc = cli.main(["--env-file", str(env_file), "--account", "codecrew", "auth", "x"], transport=transport, environ={})
    out, err = capsys.readouterr()
    assert rc == 0
    assert "Signed in to X as @crewworks, open:" in out and "https://api.x.com/oauth/authorize?oauth_token=reqtok" in out
    assert prompts == ["3. Enter the PIN: "]
    assert "Tokens for @crewworks (77) stored as CODECREW_X_ACCESS_TOKEN, CODECREW_X_ACCESS_TOKEN_SECRET" in out
    for secret in ("newtok", "newsec", "reqsec", "xsecret", "crewtoken"):
        assert secret not in out and secret not in err
    text = env_file.read_text()
    assert "CODECREW_X_ACCESS_TOKEN=newtok\n" in text and "CODECREW_X_ACCESS_TOKEN_SECRET=newsec\n" in text
    assert "X_ACCESS_TOKEN=xtoken\n" in text and "X_ACCESS_TOKEN_SECRET=xtokensecret\n" in text  # Radius Red's untouched
    assert transport.calls[1]["body"] == b"oauth_verifier=7654321"
    assert 'oauth_consumer_key="xkey"' in transport.calls[0]["headers"]["Authorization"]  # the shared app


def test_auth_x_for_radiusred_persists_under_the_bare_keys(env_file, transport, monkeypatch, capsys):
    _pin_flow(transport, screen_name="Example_UK")
    monkeypatch.setattr("builtins.input", lambda _: "1")
    rc = cli.main(["--env-file", str(env_file), "auth", "x"], transport=transport, environ={})
    assert rc == 0
    assert "stored as X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET" in capsys.readouterr().out
    text = env_file.read_text()
    assert "X_ACCESS_TOKEN=newtok\n" in text and "CODECREW_X_ACCESS_TOKEN=crewtoken\n" in text


def test_auth_x_refuses_tokens_for_another_account_and_stores_nothing(env_file, transport, monkeypatch, capsys):
    before = env_file.read_text()
    _pin_flow(transport, screen_name="example_uk")  # signed in as Radius Red by mistake
    monkeypatch.setattr("builtins.input", lambda _: "1")
    rc = cli.main(["--env-file", str(env_file), "--account", "codecrew", "auth", "x"], transport=transport, environ={})
    out = capsys.readouterr().out
    assert rc == 1
    assert "error: the tokens belong to @example_uk, not @crewworks (CODECREW_X_HANDLE) — nothing stored" in out
    assert "newtok" not in out and env_file.read_text() == before


@pytest.mark.parametrize(
    "failing_leg, status, body",
    [
        ("/oauth/request_token", 401, b'{"errors":[{"code":32,"message":"Could not authenticate you. oauth_consumer_key=xkey oauth_signature=LEAKSIG"}]}'),
        ("/oauth/access_token", 401, b"oauth_token=LEAKTOKEN&oauth_token_secret=LEAKSECRET&error=Invalid+or+expired+token"),
        ("/oauth/access_token", 200, b"oauth_token_secret=LEAKSECRET&screen_name=crewworks"),  # a 200 with no token is a failure too
    ],
)
def test_auth_x_token_endpoint_failures_are_reported_without_the_body_and_store_nothing(
    env_file, transport, monkeypatch, capsys, failing_leg, status, body
):
    before = env_file.read_text()
    if failing_leg == "/oauth/access_token":
        transport.expect("POST", "/oauth/request_token", body=b"oauth_token=reqtok&oauth_token_secret=REQSECRET&oauth_callback_confirmed=true")
    transport.expect("POST", failing_leg, status=status, body=body)
    monkeypatch.setattr("builtins.input", lambda _: "1234567")
    rc = cli.main(["--env-file", str(env_file), "--account", "codecrew", "auth", "x"], transport=transport, environ={})
    out, err = capsys.readouterr()
    assert rc == 1
    assert "nothing stored" in out and f"HTTP {status}" in out
    step = "request token" if failing_leg.endswith("request_token") else "PIN exchange"
    assert f"X refused the {step}" in out
    for sentinel in ("LEAKTOKEN", "LEAKSECRET", "LEAKSIG", "REQSECRET", "xsecret", "Could not authenticate", "Invalid or expired"):
        assert sentinel not in out and sentinel not in err, sentinel
    assert env_file.read_text() == before


def test_auth_x_needs_the_accounts_handle_and_the_app_keys_first(env_file, refusing_transport, capsys):
    env_file.write_text(env_file.read_text().replace("CODECREW_X_HANDLE=crewworks\n", ""))
    rc = cli.main(["--env-file", str(env_file), "--account", "codecrew", "auth", "x"], transport=refusing_transport, environ={})
    assert rc == 2
    assert "error: CODECREW_X_HANDLE is not set" in capsys.readouterr().err


def test_auth_x_with_an_empty_pin_stops_before_the_exchange(env_file, transport, monkeypatch, capsys):
    transport.expect("POST", "/oauth/request_token", body=b"oauth_token=reqtok&oauth_token_secret=reqsec&oauth_callback_confirmed=true")
    monkeypatch.setattr("builtins.input", lambda _: "  ")
    rc = cli.main(["--env-file", str(env_file), "--account", "codecrew", "auth", "x"], transport=transport, environ={})
    assert rc == 1 and "error: no PIN given" in capsys.readouterr().out
    assert len(transport.calls) == 1


def test_auth_x_env_sourced_tokens_are_not_written_and_the_warning_says_so(env_file, transport, monkeypatch, capsys):
    _pin_flow(transport)
    monkeypatch.setattr("builtins.input", lambda _: "1")
    environ = {"CODECREW_X_ACCESS_TOKEN": "injected", "CODECREW_X_ACCESS_TOKEN_SECRET": "injected-s"}
    rc = cli.main(["--env-file", str(env_file), "--account", "codecrew", "auth", "x"], transport=transport, environ=environ)
    out, err = capsys.readouterr()
    assert rc == 0
    assert "NOT persisted for CODECREW_X_ACCESS_TOKEN, CODECREW_X_ACCESS_TOKEN_SECRET" in err
    assert "Tokens for @crewworks (77)" in out and "stored as" not in out
    assert "CODECREW_X_ACCESS_TOKEN=crewtoken\n" in env_file.read_text()


# --- replies (www#91, M10-R2) -------------------------------------------------


def test_x_reply_to_an_id_or_status_url_posts_a_reply(env_file, transport, capsys):
    transport.expect("POST", "/2/tweets", status=201, body={"data": {"id": "43"}})
    rc = cli.main(["--env-file", str(env_file), "post", "--to", "x", "--reply-to", "https://x.com/someone/status/42", "--text", "thanks"], transport=transport, environ={})
    assert rc == 0
    assert json.loads(capsys.readouterr().out) == {"network": "x", "id": "43", "url": "https://x.com/example_uk/status/43"}
    assert transport.bodies()[0] == {"text": "thanks", "reply": {"in_reply_to_tweet_id": "42"}}


def test_x_reply_dry_run_shows_the_reply_body(env_file, refusing_transport, capsys):
    rc = cli.main(["--env-file", str(env_file), "post", "--to", "x", "--reply-to", "42", "--text", "thanks", "--dry-run"], transport=refusing_transport, environ={})
    assert rc == 0
    assert json.loads(capsys.readouterr().out)["request"]["body"] == {"text": "thanks", "reply": {"in_reply_to_tweet_id": "42"}}


def test_bluesky_reply_fetches_the_parent_and_sets_root_and_parent(env_file, transport, capsys):
    _bluesky_login(transport)
    transport.expect("GET", "app.bsky.feed.getPosts", body={"posts": [{
        "uri": "at://did:plc:op/app.bsky.feed.post/mid", "cid": "bafymid",
        "record": {"text": "a reply", "reply": {"root": {"uri": "at://did:plc:op/app.bsky.feed.post/first", "cid": "bafyroot"}, "parent": {"uri": "at://did:plc:op/app.bsky.feed.post/first", "cid": "bafyroot"}}},
    }]})
    transport.expect("POST", "createRecord", body={"uri": "at://did:plc:abc/app.bsky.feed.post/3r", "cid": "c"})
    rc = cli.main(["--env-file", str(env_file), "post", "--to", "bluesky", "--reply-to", "at://did:plc:op/app.bsky.feed.post/mid", "--text", "thanks"], transport=transport, environ={})
    assert rc == 0
    assert json.loads(capsys.readouterr().out)["url"] == "https://bsky.app/profile/example.bsky.social/post/3r"
    record = transport.bodies()[-1]["record"]
    assert record["text"] == "thanks"
    assert record["reply"] == {
        "root": {"uri": "at://did:plc:op/app.bsky.feed.post/first", "cid": "bafyroot"},
        "parent": {"uri": "at://did:plc:op/app.bsky.feed.post/mid", "cid": "bafymid"},
    }


def test_bluesky_reply_to_a_bsky_app_url_resolves_the_handle(env_file, transport, capsys):
    transport.expect("GET", "resolveHandle", body={"did": "did:plc:op"})
    _bluesky_login(transport)
    transport.expect("GET", "app.bsky.feed.getPosts", body={"posts": [{"uri": "at://did:plc:op/app.bsky.feed.post/3k", "cid": "c1", "record": {"text": "top"}}]})
    transport.expect("POST", "createRecord", body={"uri": "at://did:plc:abc/app.bsky.feed.post/3r", "cid": "c"})
    rc = cli.main(["--env-file", str(env_file), "post", "--to", "bluesky", "--reply-to", "https://bsky.app/profile/op.example/post/3k", "--text", "thanks"], transport=transport, environ={})
    assert rc == 0
    parent = {"uri": "at://did:plc:op/app.bsky.feed.post/3k", "cid": "c1"}
    assert transport.bodies()[-1]["record"]["reply"] == {"root": parent, "parent": parent}


def test_bluesky_reply_dry_run_touches_no_network_and_marks_the_refs_as_fetched_later(env_file, refusing_transport, capsys):
    rc = cli.main(["--env-file", str(env_file), "post", "--to", "bluesky", "--reply-to", "https://bsky.app/profile/op.example/post/3k", "--text", "thanks", "--dry-run"], transport=refusing_transport, environ={})
    assert rc == 0
    reply = json.loads(capsys.readouterr().out)["request"]["body"]["record"]["reply"]
    assert reply["parent"]["uri"] == "at://op.example/app.bsky.feed.post/3k"
    assert "fetched at send time" in reply["parent"]["cid"] and "fetched at send time" in reply["root"]["uri"]


def test_bluesky_reply_lookup_failure_is_reported_and_nothing_is_posted(env_file, transport, capsys):
    _bluesky_login(transport)
    transport.expect("GET", "app.bsky.feed.getPosts", body={"posts": []})
    rc = cli.main(["--env-file", str(env_file), "post", "--to", "bluesky", "--reply-to", "at://did:plc:op/app.bsky.feed.post/gone", "--text", "thanks"], transport=transport, environ={})
    assert rc == 1
    assert json.loads(capsys.readouterr().out) == {"network": "bluesky", "error": "no post at at://did:plc:op/app.bsky.feed.post/gone"}
    assert not any("createRecord" in c["url"] for c in transport.calls)


def test_reply_to_is_one_network_per_invocation_and_never_linkedin(env_file, refusing_transport):
    for to in (["--to", "bluesky", "--to", "x"], ["--to", "linkedin"], []):
        with pytest.raises(SystemExit, match="one network per invocation|--to x is required"):
            cli.main(["--env-file", str(env_file), "post", *to, "--reply-to", "42", "--text", "hi"], transport=refusing_transport, environ={})


def test_reply_to_with_a_ref_for_the_other_network_is_a_usage_error_before_any_call(env_file, refusing_transport, capsys):
    rc = cli.main(["--env-file", str(env_file), "post", "--to", "x", "--reply-to", "at://did:plc:a/app.bsky.feed.post/b", "--text", "hi"], transport=refusing_transport, environ={})
    assert rc == 2 and "is not an X post ID or status URL" in capsys.readouterr().err
    rc = cli.main(["--env-file", str(env_file), "post", "--to", "bluesky", "--reply-to", "42", "--text", "hi"], transport=refusing_transport, environ={})
    assert rc == 2 and "is not a Bluesky post at:// URI or bsky.app post URL" in capsys.readouterr().err


# --- X post plus its link reply in one go (www#91, M10-R2) -------------------


@pytest.fixture
def links_file(tmp_path):
    path = tmp_path / "links.txt"
    path.write_text("https://codecrew.works/ and https://www.radiusred.uk/blog/\n")
    return path


def test_x_reply_file_posts_then_replies_and_prints_both_urls(env_file, transport, links_file, capsys):
    transport.expect("POST", "/2/tweets", status=201, body={"data": {"id": "100"}})
    transport.expect("POST", "/2/tweets", status=201, body={"data": {"id": "101"}})
    rc = cli.main(["--env-file", str(env_file), "--account", "codecrew", "post", "--to", "x", "--text", "Shipped 2.2, links below", "--x-reply-file", str(links_file)], transport=transport, environ={})
    assert rc == 0
    lines = [json.loads(l) for l in capsys.readouterr().out.splitlines()]
    assert lines == [
        {"network": "x", "id": "100", "url": "https://x.com/crewworks/status/100"},
        {"network": "x", "reply_to": "100", "id": "101", "url": "https://x.com/crewworks/status/101"},
    ]
    post, reply = transport.bodies()
    assert post == {"text": "Shipped 2.2, links below"}
    assert reply == {"text": "https://codecrew.works/ and https://www.radiusred.uk/blog/", "reply": {"in_reply_to_tweet_id": "100"}}


def test_x_reply_file_dry_run_shows_both_requests(env_file, refusing_transport, links_file, capsys):
    rc = cli.main(["--env-file", str(env_file), "post", "--to", "x", "--text", "Shipped", "--x-reply-file", str(links_file), "--dry-run"], transport=refusing_transport, environ={})
    assert rc == 0
    out = capsys.readouterr().out
    docs = [json.loads(chunk) for chunk in out.replace("}\n{", "}\n\x00{").split("\x00")]
    assert [d["request"]["body"] for d in docs] == [
        {"text": "Shipped"},
        {"text": "https://codecrew.works/ and https://www.radiusred.uk/blog/", "reply": {"in_reply_to_tweet_id": "<the post's id>"}},
    ]


def test_x_reply_file_refuses_a_url_in_the_body_before_any_network_call(env_file, refusing_transport, links_file, capsys):
    for body in ("Shipped: https://codecrew.works/", "Shipped, see codecrew.works"):
        rc = cli.main(["--env-file", str(env_file), "post", "--to", "x", "--text", body, "--x-reply-file", str(links_file)], transport=refusing_transport, environ={})
        assert rc == 2
        err = capsys.readouterr().err
        assert "error: the X post body carries a URL (" in err and "codecrew.works" in err and "the links go in the reply" in err


def test_x_reply_file_checks_the_reply_length_before_any_network_call(env_file, refusing_transport, tmp_path, capsys):
    long_reply = tmp_path / "long.txt"
    long_reply.write_text("a" * 281)
    rc = cli.main(["--env-file", str(env_file), "post", "--to", "x", "--text", "Shipped", "--x-reply-file", str(long_reply)], transport=refusing_transport, environ={})
    assert rc == 2 and "281 weighted characters" in capsys.readouterr().err


def test_x_reply_file_failure_reports_the_first_url_and_the_retry_command(env_file, transport, links_file, capsys):
    transport.expect("POST", "/2/tweets", status=201, body={"data": {"id": "100"}})
    transport.expect("POST", "/2/tweets", status=402, body={"title": "Payment Required", "detail": "credits depleted", "type": "https://api.x.com/2/problems/credits-depleted"})
    rc = cli.main(["--env-file", str(env_file), "post", "--to", "x", "--text", "Shipped", "--x-reply-file", str(links_file)], transport=transport, environ={})
    assert rc == 1
    out, err = capsys.readouterr()
    lines = [json.loads(l) for l in out.splitlines()]
    assert lines[0] == {"network": "x", "id": "100", "url": "https://x.com/example_uk/status/100"}
    assert lines[1]["reply_to"] == "100" and lines[1]["error"].startswith("X reply failed: out of credits — ")
    assert "x: the post is up at https://x.com/example_uk/status/100 but its reply failed" in err
    assert f"uv run -m social --env-file {env_file} --account radiusred post --to x --reply-to 100 --text-file {links_file}" in err


def test_x_reply_file_needs_to_x_and_excludes_reply_to(env_file, refusing_transport, links_file):
    with pytest.raises(SystemExit, match="--x-reply-file needs --to x"):
        cli.main(["--env-file", str(env_file), "post", "--to", "bluesky", "--text", "hi", "--x-reply-file", str(links_file)], transport=refusing_transport, environ={})
    with pytest.raises(SystemExit, match="cannot be combined with --reply-to"):
        cli.main(["--env-file", str(env_file), "post", "--to", "x", "--reply-to", "1", "--text", "hi", "--x-reply-file", str(links_file)], transport=refusing_transport, environ={})


def test_x_reply_file_alongside_bluesky_replies_on_x_only(env_file, transport, links_file, capsys):
    _bluesky_login(transport)
    transport.expect("POST", "createRecord", body={"uri": "at://did:plc:abc/app.bsky.feed.post/3k", "cid": "c"})
    transport.expect("POST", "/2/tweets", status=201, body={"data": {"id": "100"}})
    transport.expect("POST", "/2/tweets", status=201, body={"data": {"id": "101"}})
    rc = cli.main(["--env-file", str(env_file), "post", "--to", "bluesky", "--to", "x", "--text", "Shipped", "--x-reply-file", str(links_file)], transport=transport, environ={})
    assert rc == 0
    assert [(d["network"], d.get("reply_to")) for d in map(json.loads, capsys.readouterr().out.splitlines())] == [("bluesky", None), ("x", None), ("x", "100")]
