"""The banner originals and the social banner files (M11-R4)."""

from pathlib import Path

import pytest
from PIL import Image, ImageChops

ORIGINALS = Path("brand/originals")
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
