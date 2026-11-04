"""Built pages carry plain, escaped titles (M13-R1, M13-R3).

Zensical 0.0.74 uses the nav label as page.title, and a blog post's nav label
holds its date as HTML (`<small class="muted">`). Written unescaped into
og:title, its quotes ended the attribute and the rest of the tag showed as
text at the top of every blog post page. These tests build the site from a
copy of docs/ and zensical.toml and read the <head> of every built page.
"""

import re
import shutil
import subprocess
import sys
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

import pytest

from main import parse_frontmatter

SITE_NAME = "Radius Red"
HOME_TITLE = "Radius Red — Agentic Engineering, Human Consulting"
TAG = re.compile(r"<[A-Za-z/!]")
TITLE = re.compile(r"<title>(.*?)</title>", re.DOTALL)


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    root = tmp_path_factory.mktemp("build")
    shutil.copytree("docs", root / "docs")
    shutil.copy("zensical.toml", root / "zensical.toml")
    zensical = Path(sys.executable).parent / "zensical"
    subprocess.run([str(zensical), "build", "--clean"], cwd=root, check=True, capture_output=True)
    return root / "site"


class _Head(HTMLParser):
    """Collect the content of every <meta> tag, keyed by its property or name."""

    def __init__(self):
        super().__init__()
        self.meta = []

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            a = dict(attrs)
            if "content" in a:
                self.meta.append((a.get("property") or a.get("name"), a["content"] or ""))


def _head(page):
    html = page.read_text()
    parser = _Head()
    parser.feed(html)
    titles = [unescape(t) for t in TITLE.findall(html)]
    return titles, parser.meta


def _pages(site):
    pages = sorted(site.rglob("*.html"))
    assert pages, f"no pages built under {site}"
    return pages


def test_no_title_or_meta_content_holds_a_tag(site):
    bad = []
    for page in _pages(site):
        titles, meta = _head(page)
        bad += [f"{page.relative_to(site)}: <title> {t!r}" for t in titles if TAG.search(t)]
        bad += [f"{page.relative_to(site)}: {key} {value!r}" for key, value in meta if TAG.search(value)]
    assert not bad, "markup in a page title or meta content:\n" + "\n".join(bad)


def test_a_blog_post_has_its_front_matter_title_in_all_three_places(site):
    posts = sorted(Path("docs/blog/posts").glob("*.md"))
    assert posts
    for post in posts:
        fm, _ = parse_frontmatter(post.read_text())
        want = f"{fm['title']} - {SITE_NAME}"
        titles, meta = _head(site / "blog/posts" / post.stem / "index.html")
        meta = dict(meta)
        assert titles == [want], post.name
        assert meta["og:title"] == want, post.name
        assert meta["twitter:title"] == want, post.name


def test_the_home_page_keeps_the_branded_title(site):
    titles, meta = _head(site / "index.html")
    meta = dict(meta)
    assert titles == [HOME_TITLE]
    assert meta["og:title"] == HOME_TITLE
    assert meta["twitter:title"] == HOME_TITLE
