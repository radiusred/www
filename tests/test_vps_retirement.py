"""The rsync-over-SSH deploy remnants stay gone from the repo (M4-R2).

The VPS www vhost was decommissioned under radiusred/www#64 and the
provisioning script and WWW_* secrets went with it. These tests pin that
none of it drifts back into the tree or the operator docs.
"""

from pathlib import Path

RETIRED = ("WWW_SSH_DEPLOY_KEY", "WWW_VPS_HOST_KEY", "provision-vps.sh")


def _current_text(doc):
    """The document minus its History section: history may name what went."""
    text = Path(doc).read_text()
    return text.split("\n## History", 1)[0]


def test_provisioning_script_and_its_directory_are_gone():
    assert not Path("ops/provision-vps.sh").exists()
    assert not Path("ops").exists(), "ops/ held only the VPS provisioning script"


def test_operator_docs_no_longer_name_the_retired_secrets_or_script():
    for doc in ("README.md", "RUNBOOK.md"):
        text = _current_text(doc)
        for name in RETIRED:
            assert name not in text, f"{name!r} still appears in {doc} outside History"


def test_runbook_describes_the_pages_deploy_behind_cloudflare():
    text = _current_text("RUNBOOK.md")
    assert ".github/workflows/docs.yml" in text
    assert "radiusred.github.io" in text
    assert "Cloudflare" in text
    for stale in ("rsync", "certbot", "/var/www/", "sites-available"):
        assert stale not in text, f"{stale!r} still describes the retired VPS in RUNBOOK.md"
