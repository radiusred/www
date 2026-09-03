import pytest

import sync_docs
from sync_docs import PROJECTS, project_nav_entries, sync_project, write_projects_nav

README = (
    "# Demo\n\n"
    "See the [quickstart](docs/first-milestone.md#start), the\n"
    "[contributing guide](CONTRIBUTING.md) and the [spec](SPEC.md).\n"
)


@pytest.fixture
def source_tree(tmp_path, monkeypatch):
    """A fake sibling checkout under a scratch SYNC_SOURCE_BASE, with the
    sync's destination and config rooted in the same scratch dir."""
    base = tmp_path / "_sources"
    repo = base / "demo"
    (repo / "docs" / "milestones").mkdir(parents=True)
    (repo / "README.md").write_text(README, encoding="utf-8")
    (repo / "CONTRIBUTING.md").write_text("# Contributing\n", encoding="utf-8")
    (repo / "SECURITY.md").write_text("# Security\n", encoding="utf-8")
    (repo / "docs" / "first-milestone.md").write_text("# Your first milestone\n", encoding="utf-8")
    (repo / "docs" / "milestones" / "1.md").write_text("# M1\n", encoding="utf-8")

    monkeypatch.setenv("SYNC_SOURCE_BASE", str(base))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sync_docs, "DEST_BASE", tmp_path / "docs" / "projects")
    monkeypatch.setattr(sync_docs, "CONFIG", tmp_path / "zensical.toml")
    (tmp_path / "zensical.toml").write_text(
        "nav = [\n    # BEGIN_PROJECTS_NAV\n    # END_PROJECTS_NAV\n]\n", encoding="utf-8"
    )
    return tmp_path


def synced_files(dest):
    return sorted(p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file())


def test_readme_only_syncs_the_readme_and_nothing_else(source_tree):
    project = {"name": "demo", "repo": "org/demo", "branch": "main", "readme_only": True}
    dest = sync_docs.DEST_BASE / "demo"

    assert sync_project(project) is True
    assert synced_files(dest) == ["index.md"]

    index = (dest / "index.md").read_text(encoding="utf-8")
    assert "(https://github.com/org/demo/blob/main/docs/first-milestone.md#start)" in index
    assert "(https://github.com/org/demo/blob/main/CONTRIBUTING.md)" in index
    assert "(https://github.com/org/demo/blob/main/SPEC.md)" in index


def test_default_project_still_syncs_docs_tree_and_root_files(source_tree):
    project = {"name": "demo", "repo": "org/demo", "branch": "main", "exclude": ["milestones/"]}
    dest = sync_docs.DEST_BASE / "demo"

    assert sync_project(project) is True
    assert synced_files(dest) == ["contributing.md", "first-milestone.md", "index.md", "security.md"]

    index = (dest / "index.md").read_text(encoding="utf-8")
    assert "(first-milestone.md#start)" in index
    assert "(contributing.md)" in index


def test_readme_only_nav_collapses_to_a_single_overview_entry(source_tree):
    project = {"name": "demo", "repo": "org/demo", "branch": "main", "readme_only": True}
    dest = sync_docs.DEST_BASE / "demo"
    sync_project(project)

    entries = project_nav_entries(project, dest)
    assert entries == [("Overview", "projects/demo/index.md")]

    write_projects_nav([(project, entries)])
    config = sync_docs.CONFIG.read_text(encoding="utf-8")
    assert '    { "demo" = "projects/demo/index.md" },\n' in config
    assert "first-milestone" not in config


def test_gh_codecrew_is_synced_readme_only():
    """codecrew.works is the canonical home for CodeCrew's docs; www carries
    only the README (radiusred/www#59)."""
    (project,) = [p for p in PROJECTS if p["name"] == "gh-codecrew"]
    assert project.get("readme_only") is True
    assert "exclude" not in project
