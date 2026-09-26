import os
from pathlib import Path

import pytest

from social import config
from social.config import Credentials, MissingCredential, load_credentials, parse_env_file


def test_parse_env_file_skips_comments_and_strips_quotes():
    parsed = parse_env_file("# c\n\nA=1\nB = 'two' \nC=\"th=ree\"\nnot a pair\n")
    assert parsed == {"A": "1", "B": "two", "C": "th=ree"}


def test_environment_wins_over_file_key_by_key(env_file):
    creds = load_credentials(env_file, {"BSKY_HANDLE": "override.bsky.social"})
    assert creds.get("BSKY_HANDLE") == "override.bsky.social"
    assert creds.get("BSKY_APP_PASSWORD") == "app-pass"
    assert creds.from_env == {"BSKY_HANDLE"}


def test_missing_file_is_fine_and_require_names_it(tmp_path):
    creds = load_credentials(tmp_path / "absent.env", {})
    assert creds.get("BSKY_HANDLE") is None
    try:
        creds.require("BSKY_HANDLE")
    except MissingCredential as err:
        assert "absent.env" in str(err)
    else:
        raise AssertionError("expected MissingCredential")


def test_persist_rewrites_in_place_and_appends_new_keys(env_file):
    creds = load_credentials(env_file, {})
    skipped = creds.persist({"LINKEDIN_ACCESS_TOKEN": "new-access", "LINKEDIN_ORG_URN": "urn:li:organization:7", "NEW_KEY": "x"})
    assert skipped == []
    text = env_file.read_text()
    assert text.startswith("# test creds\n")
    assert "LINKEDIN_ACCESS_TOKEN=new-access\n" in text
    assert text.count("LINKEDIN_ACCESS_TOKEN=") == 1
    assert text.endswith("NEW_KEY=x\n")
    assert oct(os.stat(env_file).st_mode & 0o777) == "0o600"
    assert creds.get("LINKEDIN_ORG_URN") == "urn:li:organization:7"


def test_persist_never_writes_values_that_came_from_the_environment(env_file):
    creds = load_credentials(env_file, {"LINKEDIN_ACCESS_TOKEN": "from-env"})
    skipped = creds.persist({"LINKEDIN_ACCESS_TOKEN": "rotated", "LINKEDIN_ACCESS_TOKEN_EXPIRES_AT": "123"})
    assert skipped == ["LINKEDIN_ACCESS_TOKEN"]
    text = env_file.read_text()
    assert "LINKEDIN_ACCESS_TOKEN=old-access\n" in text
    assert "LINKEDIN_ACCESS_TOKEN_EXPIRES_AT=123\n" in text
    assert creds.get("LINKEDIN_ACCESS_TOKEN") == "rotated"  # in memory for this run


def test_persist_without_a_file_reports_everything_skipped():
    creds = Credentials(values={}, from_env=set(), env_file=None)
    assert creds.persist({"A": "1", "B": "2"}) == ["A", "B"]


def test_persist_creates_the_file_and_directory_private_from_the_start(tmp_path):
    target = tmp_path / "cfg" / "social.env"
    creds = Credentials(values={}, from_env=set(), env_file=target)
    assert creds.persist({"A": "1"}) == []
    assert oct(os.stat(target).st_mode & 0o777) == "0o600"
    assert oct(os.stat(target.parent).st_mode & 0o777) == "0o700"


# --- the default path and the transitional fallback (www#70, M7-R5) ---------


@pytest.fixture
def paths(tmp_path, monkeypatch):
    """Both default paths pointed into tmp_path — never the real home."""
    new = tmp_path / "radiusred" / "social.env"
    old = tmp_path / "codecrew" / "social.env"
    monkeypatch.setattr(config, "DEFAULT_ENV_FILE", new)
    monkeypatch.setattr(config, "LEGACY_ENV_FILE", old)
    return new, old


def _write(path, text="BSKY_HANDLE=from-file\n"):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(text)


def test_default_paths_are_radiusred_with_codecrew_as_the_legacy():
    assert config.DEFAULT_ENV_FILE == Path.home() / ".config" / "radiusred" / "social.env"
    assert config.LEGACY_ENV_FILE == Path.home() / ".config" / "codecrew" / "social.env"


def test_new_path_is_read_when_present_with_no_hint(paths, capsys):
    new, old = paths
    _write(new, "BSKY_HANDLE=new\n")
    _write(old, "BSKY_HANDLE=old\n")  # ignored once the new file exists
    creds = load_credentials(None, {})
    assert creds.get("BSKY_HANDLE") == "new"
    assert creds.env_file == new and creds.seed_from is None
    assert capsys.readouterr().err == ""


def test_old_path_is_read_when_the_new_one_is_absent_with_one_hint_naming_both(paths, capsys):
    new, old = paths
    _write(old, "BSKY_HANDLE=old\n")
    creds = load_credentials(None, {})
    assert creds.get("BSKY_HANDLE") == "old"
    assert creds.env_file == new  # writes go to the new path only
    assert creds.seed_from == old
    err = capsys.readouterr().err
    assert err.count("\n") == 1
    assert str(new) in err and str(old) in err and "move" in err


def test_neither_path_present_binds_the_new_path_and_says_nothing(paths, capsys):
    new, old = paths
    creds = load_credentials(None, {})
    assert creds.values == {} and creds.env_file == new and creds.seed_from is None
    assert capsys.readouterr().err == ""
    try:
        creds.require("BSKY_HANDLE")
    except MissingCredential as err:
        assert str(new) in str(err) and str(old) not in str(err)
    else:
        raise AssertionError("expected MissingCredential")


def test_explicit_env_file_never_falls_back_and_never_hints(paths, tmp_path, capsys):
    new, old = paths
    _write(old, "BSKY_HANDLE=old\n")
    mine = tmp_path / "mine.env"
    creds = load_credentials(mine, {})
    assert creds.get("BSKY_HANDLE") is None
    assert creds.env_file == mine and creds.seed_from is None
    assert capsys.readouterr().err == ""


def test_persist_from_the_fallback_seeds_the_new_file_with_the_full_value_set(paths):
    new, old = paths
    legacy_text = "# operator's file\nBSKY_HANDLE=old\nBSKY_APP_PASSWORD=pw\nLINKEDIN_ACCESS_TOKEN=stale\n"
    _write(old, legacy_text)
    creds = load_credentials(None, {})
    assert creds.persist({"LINKEDIN_ACCESS_TOKEN": "fresh", "LINKEDIN_ACCESS_TOKEN_EXPIRES_AT": "9"}) == []
    assert new.read_text() == (
        "# operator's file\nBSKY_HANDLE=old\nBSKY_APP_PASSWORD=pw\nLINKEDIN_ACCESS_TOKEN=fresh\n"
        "LINKEDIN_ACCESS_TOKEN_EXPIRES_AT=9\n"
    )
    assert old.read_text() == legacy_text  # the old path is never written
    assert oct(os.stat(new).st_mode & 0o777) == "0o600"
    assert oct(os.stat(new.parent).st_mode & 0o777) == "0o700"
    # a second write in the same run edits the new file, not the legacy text again
    creds.persist({"LINKEDIN_ORG_URN": "urn:li:organization:1"})
    text = new.read_text()
    assert text.count("LINKEDIN_ACCESS_TOKEN=fresh\n") == 1 and text.endswith("LINKEDIN_ORG_URN=urn:li:organization:1\n")
    assert old.read_text() == legacy_text
