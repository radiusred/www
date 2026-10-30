"""The banner originals, the social banner files and the link preview (M11-R2, M11-R4)."""

import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest
from PIL import Image, ImageChops

ORIGINALS = Path("brand/originals")
PREVIEW = Path("docs/assets/images/social-preview.png")
PREVIEW_URL = "https://www.radiusred.uk/assets/images/social-preview.png"
BACKGROUND = (17, 17, 17)

# file: (size, the box the wordmark must stay in, the profile picture's corner)
SOCIAL = {
    "brand/social/x-header.png": ((1500, 500), (420, 40, 1460, 460), (40, 333, 375, 500)),
    "brand/social/bluesky-banner.png": ((3000, 1000), (600, 100, 2900, 900), (50, 775, 500, 1000)),
    "brand/social/linkedin-cover.png": ((4200, 700), (700, 130, 4100, 570), (90, 475, 566, 700)),
}


def _content_box(path):
    """The bounding box of every pixel that is not the background colour."""
    im = Image.open(path).convert("RGB")
    diff = ImageChops.difference(im, Image.new("RGB", im.size, BACKGROUND))
    return diff.convert("L").point(lambda v: 255 if v > 2 else 0).getbbox()


def _inside(inner, outer):
    return inner[0] >= outer[0] and inner[1] >= outer[1] and inner[2] <= outer[2] and inner[3] <= outer[3]


def _overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def test_the_four_originals_are_kept_at_full_size():
    names = sorted(p.name for p in ORIGINALS.glob("*.png"))
    assert names == ["banner-black-bg.png", "banner-blacktext.png", "banner-white-bg.png", "banner-whitetext.png"]
    for name in names:
        assert Image.open(ORIGINALS / name).size == (4210, 859), name


@pytest.mark.parametrize("name", SOCIAL)
def test_social_banner_keeps_the_wordmark_clear_of_the_profile_picture(name):
    size, box, avatar = SOCIAL[name]
    im = Image.open(name)
    assert im.format == "PNG"
    assert im.size == size
    content = _content_box(name)
    assert content is not None
    assert _inside(content, box), content
    assert not _overlaps(content, avatar), content


def test_preview_is_a_1200_by_630_png_of_the_black_banner():
    im = Image.open(PREVIEW)
    assert im.format == "PNG"
    assert im.size == (1200, 630)
    assert im.convert("RGB").getpixel((0, 0)) == BACKGROUND


def test_template_has_no_todo():
    assert "TODO" not in Path("docs/overrides/main.html").read_text()


class _Meta(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = {}

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            a = dict(attrs)
            key = a.get("property") or a.get("name")
            if key:
                self.tags.setdefault(key, []).append(a.get("content"))


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    """Build the site from a copy of the repository's config and docs."""
    root = tmp_path_factory.mktemp("build")
    shutil.copy("zensical.toml", root)
    shutil.copytree("docs", root / "docs")
    subprocess.run(["zensical", "build", "--clean"], cwd=root, check=True, capture_output=True)
    return root / "site"


def test_every_page_declares_the_absolute_preview_with_size_and_alt(site):
    # The build also copies the template source to site/overrides/; it is not a page.
    pages = sorted(p for p in site.rglob("*.html") if p.parts[len(site.parts)] != "overrides")
    assert len(pages) > 5
    for page in pages:
        p = _Meta()
        p.feed(page.read_text())
        t = p.tags
        where = page.relative_to(site)
        assert t.get("og:image") == [PREVIEW_URL], where
        assert t.get("twitter:image") == [PREVIEW_URL], where
        assert t.get("og:image:width") == ["1200"], where
        assert t.get("og:image:height") == ["630"], where
        assert t.get("og:image:type") == ["image/png"], where
        alt = t.get("og:image:alt")
        assert alt and alt[0], where
        assert t.get("twitter:image:alt") == alt, where


def test_the_preview_is_published_and_brand_is_not(site):
    assert (site / "assets/images/social-preview.png").is_file()
    assert not list(site.rglob("banner-black-bg.png"))
    assert not list(site.rglob("x-header.png"))
