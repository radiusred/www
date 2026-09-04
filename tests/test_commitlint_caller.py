"""Commit messages are linted through the org's shared action (M5-R2).

The commitlint job in .github/workflows/ci.yml is the thin caller that
radiusred/.github's CONTRIBUTING.md documents. These tests pin its shape so
a later edit cannot quietly bring back a per-repo copy of the lint, rename
the check the org ruleset require-lint requires, or drop what the shared
action needs from its caller.
"""

from pathlib import Path

import yaml

WORKFLOW = Path(".github/workflows/ci.yml")
SHARED_ACTION = "radiusred/.github/.github/actions/commitlint@main"


def _load():
    wf = yaml.safe_load(WORKFLOW.read_text())
    # PyYAML reads the bare `on:` key as boolean True.
    wf["on"] = wf.pop(True, wf.get("on"))
    return wf


def test_commitlint_job_reports_the_check_context_the_ruleset_requires():
    assert _load()["jobs"]["commitlint"]["name"] == "Lint commit messages"


def test_commitlint_job_checks_out_full_history_then_calls_the_shared_action():
    steps = _load()["jobs"]["commitlint"]["steps"]
    assert [step["uses"] for step in steps] == ["actions/checkout@v4", SHARED_ACTION]
    assert steps[0]["with"] == {"fetch-depth": 0}


def test_workflow_grants_what_the_shared_action_needs():
    assert _load()["permissions"] == {"contents": "read", "pull-requests": "read"}


def test_no_per_repo_commitlint_copy_remains():
    assert "wagoid/" not in WORKFLOW.read_text(), "the caller must not run commitlint directly"
    assert not Path("commitlint.config.mjs").exists(), "the shared action carries the config"


def test_tests_job_is_kept():
    test = _load()["jobs"]["test"]
    assert test["name"] == "Tests"
    assert test["steps"][-1] == {"run": "uv run pytest"}
