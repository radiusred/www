import os

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
