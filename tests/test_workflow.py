"""The site deploys through GitHub Pages actions, not rsync over SSH (M4-R1).

These tests pin the shape of .github/workflows/docs.yml so that a later edit
cannot quietly bring the VPS deploy back or drop what deploy-pages needs.
"""

import re
from pathlib import Path

import yaml

WORKFLOW = Path(".github/workflows/docs.yml")


def _load():
    wf = yaml.safe_load(WORKFLOW.read_text())
    # PyYAML reads the bare `on:` key as boolean True.
    wf["on"] = wf.pop(True, wf.get("on"))
    return wf


def _uses(job):
    return [step["uses"] for step in job["steps"] if "uses" in step]


def test_build_job_uploads_the_zensical_output_as_the_pages_artifact():
    build = _load()["jobs"]["build"]
    runs = [step["run"] for step in build["steps"] if "run" in step]
    assert runs[-1] == "zensical build --clean"
    upload = [s for s in build["steps"] if s.get("uses", "").startswith("actions/upload-pages-artifact@")]
    assert len(upload) == 1
    assert upload[0]["with"] == {"path": "site"}
    assert build["steps"][-1] is upload[0], "the artifact upload must be the last build step"


def test_deploy_job_has_what_deploy_pages_needs():
    deploy = _load()["jobs"]["deploy"]
    assert deploy["needs"] == "build"
    assert deploy["permissions"] == {"pages": "write", "id-token": "write"}
    assert deploy["environment"]["name"] == "github-pages"
    assert deploy["environment"]["url"] == "${{ steps.deployment.outputs.page_url }}"
    (step,) = deploy["steps"]
    assert step["id"] == "deployment"
    assert step["uses"].startswith("actions/deploy-pages@")


def test_pages_actions_are_pinned_to_a_major_version():
    wf = _load()
    for job in wf["jobs"].values():
        for uses in _uses(job):
            if uses.startswith("actions/upload-pages-artifact@") or uses.startswith("actions/deploy-pages@"):
                assert re.fullmatch(r"actions/[a-z-]+@v\d+", uses), uses


def test_no_ssh_or_rsync_deploy_remains():
    text = WORKFLOW.read_text()
    for forbidden in ("rsync", "ssh", "secrets.", "known_hosts", "129.121.91.205"):
        assert forbidden not in text, f"{forbidden!r} still appears in {WORKFLOW}"


def test_triggers_and_concurrency_are_kept():
    wf = _load()
    assert wf["on"]["push"]["branches"] == ["main"]
    assert wf["on"]["schedule"] == [{"cron": "5 0 * * *"}]
    assert "workflow_dispatch" in wf["on"]
    assert wf["permissions"] == {"contents": "read"}
    assert wf["concurrency"] == {"group": "www-docs-deploy", "cancel-in-progress": True}
