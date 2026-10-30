"""The footer and the structured data name the live social profiles (M11-R6)."""

import json
import re
import shutil
import subprocess
from html.parser import HTMLParser

import pytest

X = "https://x.com/radiusred_uk"
BLUESKY = "https://bsky.app/profile/radiusred.uk"


class _Footer(HTMLParser):
    """The links in the footer's social block, each with whether it holds an svg icon."""

    def __init__(self):
        super().__init__()
        self.depth = 0
        self.link = None
        self.links = {}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if self.depth:
            if tag != "a":
                self.depth += 1
            if tag == "a" and "md-social__link" in (a.get("class") or ""):
                self.link = a.get("href")
                self.links[self.link] = False
            elif tag == "svg" and self.link:
                self.links[self.link] = True
        elif tag == "div" and "md-social" in (a.get("class") or "").split():
            self.depth = 1

    def handle_endtag(self, tag):
        if tag == "a":
            self.link = None
        elif self.depth:
            self.depth -= 1


@pytest.fixture(scope="module")
def pages(tmp_path_factory):
    """Build the site from a copy of the repository's config and docs."""
    root = tmp_path_factory.mktemp("build")
    shutil.copy("zensical.toml", root)
    shutil.copytree("docs", root / "docs")
    subprocess.run(["zensical", "build", "--clean"], cwd=root, check=True, capture_output=True)
    site = root / "site"
    # The build also copies the template source to site/overrides/; it is not a page.
    found = sorted(p for p in site.rglob("*.html") if p.parts[len(site.parts)] != "overrides")
    assert len(found) > 5
    return {p.relative_to(site): p.read_text() for p in found}


def test_every_footer_links_x_and_bluesky_with_an_icon(pages):
    for where, html in pages.items():
        footer = _Footer()
        footer.feed(html)
        assert footer.links.get(X) is True, where
        assert footer.links.get(BLUESKY) is True, where


def test_no_page_names_the_old_bluesky_handle(pages):
    for where, html in pages.items():
        assert "radiusred.bsky.social" not in html, where


def test_the_organization_same_as_names_both_profiles(pages):
    html = pages[next(p for p in pages if str(p) == "index.html")]
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    org = [n for b in blocks for n in json.loads(b).get("@graph", []) if n.get("@type") == "Organization"]
    assert len(org) == 1
    assert X in org[0]["sameAs"] and BLUESKY in org[0]["sameAs"]
