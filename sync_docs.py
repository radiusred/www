"""Sync documentation from sibling open-source repos into docs/projects/<name>/.

For each project, this script copies:
  README.md       -> <project>/index.md
  CONTRIBUTING.md -> <project>/contributing.md   (if present)
  SECURITY.md     -> <project>/security.md       (if present)
  docs/**         -> <project>/**                (subtree preserved, if present)

A project may list `exclude` paths (relative to its docs/ dir, e.g.
"milestones/") to leave out of the sync. Links into an excluded path are
rewritten to GitHub URLs, like any other non-synced file.

A project marked `readme_only` syncs just README.md -> <project>/index.md:
CONTRIBUTING.md, SECURITY.md and the docs/ tree are left out, and links from
the README into them are rewritten to GitHub URLs like any other non-synced
file. Use it when the project's docs have a canonical home elsewhere.

Markdown links and HTML <img src> in synced .md files are rewritten so:
  - links to other synced files resolve correctly under docs/projects/<name>/
  - links to non-synced files become absolute GitHub URLs (blob/ or raw/)
  - external URLs and in-page anchors are left alone

Source location resolution:
  Locally, sibling repos live at ../<name>. CI checks them out under
  $SYNC_SOURCE_BASE/<name>. The env var overrides the default base.

Idempotent: each project's destination is wiped before re-sync.
"""

import os
import posixpath
import re
import shutil
from pathlib import Path

PROJECTS = [
    {"name": "tradedesk", "repo": "radiusred/tradedesk", "branch": "main"},
    {"name": "tradedesk-dukascopy", "repo": "radiusred/tradedesk-dukascopy", "branch": "main"},
    {"name": "tradedesk-miner", "repo": "radiusred/tradedesk-miner", "branch": "main"},
    {"name": "ha-sinkhole", "repo": "radiusred/ha-sinkhole", "branch": "main"},
    # CodeCrew's docs live at https://codecrew.works; www carries only the
    # README as a landing page and points there for everything else.
    {"name": "gh-codecrew", "repo": "radiusred/gh-codecrew", "branch": "main", "readme_only": True},
]

DEST_BASE = Path("docs/projects")
DEFAULT_SOURCE_BASE = Path("..")
CONFIG = Path("zensical.toml")
NAV_BEGIN = "# BEGIN_PROJECTS_NAV"
NAV_END = "# END_PROJECTS_NAV"
NAV_INDENT = "    "

# Root-of-repo files that get promoted into the project landing dir.
ROOT_FILE_MAP = {
    "README.md": "index.md",
    "CONTRIBUTING.md": "contributing.md",
    "SECURITY.md": "security.md",
}

# What a readme_only project promotes: the README and nothing else.
README_ONLY_FILE_MAP = {"README.md": "index.md"}

# Image extensions get rewritten to raw.githubusercontent.com so they render.
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico"}

# Markdown link/image:  ![alt](url "title")  or  [text](url "title")
# Captures: bang, text, url, optional title (with leading whitespace).
MD_LINK_RE = re.compile(r'(!?)\[([^\]]*)\]\(([^)\s]+)(\s+"[^"]*")?\)')
# HTML <img src="...">. Matches single or double quotes.
HTML_IMG_RE = re.compile(r'(<img\b[^>]*?\bsrc=)(["\'])([^"\']+)\2', re.IGNORECASE)


def source_for(project):
    base = Path(os.environ.get("SYNC_SOURCE_BASE", DEFAULT_SOURCE_BASE))
    return base / project["name"]


def is_external(url):
    return bool(re.match(r'^[a-z][a-z0-9+\-.]*://|^mailto:|^#', url, re.IGNORECASE))


def split_anchor(path):
    """Split 'foo.md#section' into ('foo.md', '#section')."""
    if "#" in path:
        p, _, frag = path.partition("#")
        return p, "#" + frag
    return path, ""


def root_file_map(project):
    """The root-of-repo files this project promotes, keyed by source name."""
    return README_ONLY_FILE_MAP if project.get("readme_only") else ROOT_FILE_MAP


def syncs_docs_tree(project):
    return not project.get("readme_only")


def is_excluded(docs_rel, project):
    """True if `docs_rel` (relative to the upstream docs/ dir) falls under one
    of the project's `exclude` entries. A trailing slash marks a subtree."""
    for pattern in project.get("exclude", ()):
        prefix = pattern.rstrip("/")
        if docs_rel == prefix or docs_rel.startswith(prefix + "/"):
            return True
    return False


def map_to_dest(repo_path, project):
    """Map a repo-root-relative path to (dest_relpath_or_None, repo_path).

    dest_relpath is relative to the project dir (e.g. 'index.md', 'foo.md',
    'sub/bar.md'). When None, the path doesn't sync — caller should emit a
    GitHub URL using the returned repo_path.
    """
    files = root_file_map(project)
    if repo_path in files:
        return files[repo_path], repo_path
    if repo_path.startswith("docs/") and syncs_docs_tree(project):
        docs_rel = repo_path[len("docs/"):]
        if is_excluded(docs_rel, project):
            return None, repo_path
        return docs_rel, repo_path
    return None, repo_path


def github_url(repo_path, project, is_image):
    repo, branch = project["repo"], project["branch"]
    ext = posixpath.splitext(repo_path.split("#", 1)[0])[1].lower()
    use_raw = is_image or ext in IMAGE_EXTS
    host = "raw.githubusercontent.com" if use_raw else "github.com/" + repo + "/blob"
    if use_raw:
        return f"https://raw.githubusercontent.com/{repo}/{branch}/{repo_path}"
    return f"https://github.com/{repo}/blob/{branch}/{repo_path}"


def rewrite_target(url, source_repo_path, project, is_image):
    """Rewrite a single link/image target. `source_repo_path` is the original
    file's location in the upstream repo (used to resolve relative paths)."""
    if is_external(url):
        return url
    path, anchor = split_anchor(url)
    if not path:
        # Pure anchor like "#foo".
        return url

    source_dir = posixpath.dirname(source_repo_path)
    resolved = posixpath.normpath(posixpath.join(source_dir, path)) if source_dir else posixpath.normpath(path)
    if resolved.startswith("../") or resolved == "..":
        # Escapes repo root — leave the original alone.
        return url

    dest_relpath, repo_path = map_to_dest(resolved, project)
    if dest_relpath is None:
        return github_url(repo_path, project, is_image) + anchor

    # Compute relative path from this file's destination dir to the target's.
    source_dest, _ = map_to_dest(source_repo_path, project)
    source_dest_dir = posixpath.dirname(source_dest) if source_dest else ""
    rel = posixpath.relpath(dest_relpath, source_dest_dir or ".")
    return rel + anchor


def rewrite_links(content, source_repo_path, project):
    def md_replace(m):
        bang, text, url, title = m.group(1), m.group(2), m.group(3), m.group(4) or ""
        new_url = rewrite_target(url, source_repo_path, project, is_image=(bang == "!"))
        return f"{bang}[{text}]({new_url}{title})"

    def html_replace(m):
        prefix, quote, url = m.group(1), m.group(2), m.group(3)
        new_url = rewrite_target(url, source_repo_path, project, is_image=True)
        return f"{prefix}{quote}{new_url}{quote}"

    content = MD_LINK_RE.sub(md_replace, content)
    content = HTML_IMG_RE.sub(html_replace, content)
    return content


FRONTMATTER_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
H1_RE = re.compile(r'^#\s+(.+?)\s*$', re.MULTILINE)
HTML_COMMENT_RE = re.compile(r'<!--.*?-->', re.DOTALL)


def humanize(stem):
    return stem.replace("_", " ").replace("-", " ").strip().title()


def extract_title(md_path, default):
    """Read a markdown file and return its title from frontmatter, first H1,
    or a humanized filename fallback."""
    try:
        content = md_path.read_text(encoding="utf-8")
    except OSError:
        return default

    m = FRONTMATTER_RE.match(content)
    if m:
        for line in m.group(1).split("\n"):
            if ":" in line:
                key, _, value = line.partition(":")
                if key.strip() == "title":
                    return value.strip().strip('"\'')
        content = content[m.end():]

    h1 = H1_RE.search(content)
    if h1:
        title = HTML_COMMENT_RE.sub("", h1.group(1)).strip()
        if title:
            return title

    return default


def project_nav_entries(project, dest):
    """Build [(label, target)] nav entries for a synced project's pages.

    Order: index.md (Overview) first, then docs/ files alphabetically, then
    contributing.md and security.md last."""
    name = project["name"]
    entries = []

    if (dest / "index.md").exists():
        entries.append(("Overview", f"projects/{name}/index.md"))

    trailing = []
    for special, label in (("contributing.md", "Contributing"), ("security.md", "Security")):
        if (dest / special).exists():
            trailing.append((label, f"projects/{name}/{special}"))

    docs_pages = []
    for path in sorted(dest.rglob("*.md")):
        rel = path.relative_to(dest).as_posix()
        if rel in {"index.md", "contributing.md", "security.md"}:
            continue
        title = extract_title(path, default=humanize(path.stem))
        docs_pages.append((title, f"projects/{name}/{rel}"))

    return entries + docs_pages + trailing


def write_projects_nav(per_project_entries):
    """Rewrite the BEGIN_PROJECTS_NAV/END_PROJECTS_NAV block in zensical.toml.

    `per_project_entries` is a list of (project, entries) tuples in the order
    they should appear under the Projects tab."""
    inner = NAV_INDENT + "  "
    lines = [f"{NAV_INDENT}{NAV_BEGIN}"]
    for project, entries in per_project_entries:
        if not entries:
            continue
        name = project["name"].replace('"', '\\"')
        if len(entries) == 1:
            label, target = entries[0]
            lines.append(f'{NAV_INDENT}{{ "{name}" = "{target}" }},')
            continue
        lines.append(f'{NAV_INDENT}{{ "{name}" = [')
        for label, target in entries:
            safe = label.replace('"', '\\"')
            lines.append(f'{inner}{{ "{safe}" = "{target}" }},')
        lines.append(f"{NAV_INDENT}] }},")
    lines.append(f"{NAV_INDENT}{NAV_END}")

    text = CONFIG.read_text(encoding="utf-8")
    src_lines = text.split("\n")
    start = end = None
    for i, line in enumerate(src_lines):
        stripped = line.strip()
        if start is None and stripped == NAV_BEGIN:
            start = i
        elif start is not None and stripped == NAV_END:
            end = i
            break
    if start is None or end is None:
        raise RuntimeError(
            f"Could not find {NAV_BEGIN}/{NAV_END} markers in {CONFIG}"
        )
    src_lines[start : end + 1] = lines
    new_text = "\n".join(src_lines)
    if new_text != text:
        CONFIG.write_text(new_text, encoding="utf-8")
        print(f"Updated projects nav with {sum(1 for _, e in per_project_entries if e)} projects")


def sync_project(project):
    src = source_for(project)
    dest = DEST_BASE / project["name"]

    if not src.exists():
        print(f"  skip {project['name']}: source not found at {src}")
        return False

    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)

    copied = 0

    # Promoted root files.
    for src_name, dest_name in root_file_map(project).items():
        src_path = src / src_name
        if src_path.is_file():
            content = src_path.read_text(encoding="utf-8")
            content = rewrite_links(content, src_name, project)
            (dest / dest_name).write_text(content, encoding="utf-8")
            copied += 1

    # docs/ tree (subtree preserved).
    docs_src = src / "docs"
    if syncs_docs_tree(project) and docs_src.is_dir():
        for path in sorted(docs_src.rglob("*")):
            rel = path.relative_to(docs_src)
            if is_excluded(rel.as_posix(), project):
                continue
            target = dest / rel
            if path.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if path.suffix == ".md":
                repo_relpath = "docs/" + rel.as_posix()
                content = path.read_text(encoding="utf-8")
                content = rewrite_links(content, repo_relpath, project)
                target.write_text(content, encoding="utf-8")
            else:
                shutil.copy2(path, target)
            copied += 1

    if copied == 0:
        # Nothing useful to render — leave the dir empty rather than carry stub.
        shutil.rmtree(dest)
        print(f"  {project['name']}: nothing to sync (no README/CONTRIBUTING/SECURITY/docs)")
        return False

    # If there's no README upstream, drop a minimal landing so the section
    # doesn't 404 when linked from projects/index.md.
    if not (dest / "index.md").exists():
        repo = project["repo"]
        (dest / "index.md").write_text(
            f"---\ntitle: {project['name']}\n"
            f"description: Documentation for {project['name']}.\n---\n\n"
            f"# {project['name']}\n\n"
            f"Documentation imported from [{repo}](https://github.com/{repo}). "
            f"This project's repository does not yet include a `README.md`; "
            f"see the available pages in the sidebar.\n",
            encoding="utf-8",
        )
        copied += 1

    print(f"  {project['name']}: synced {copied} files")
    return True


def main():
    print(f"Syncing project docs into {DEST_BASE}/")
    DEST_BASE.mkdir(parents=True, exist_ok=True)
    per_project = []
    for project in PROJECTS:
        synced = sync_project(project)
        if synced:
            per_project.append((project, project_nav_entries(project, DEST_BASE / project["name"])))
        else:
            per_project.append((project, []))
    write_projects_nav(per_project)


if __name__ == "__main__":
    main()
