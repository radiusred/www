"""The home page shows the new banner in each theme (M11-R1).

The light theme shows the black-text banner and the dark theme the
white-text one. Both are web-optimised WebP files made from the 4210x859
transparent originals, and the old dark-text banner and every reference
to it are gone.
"""

import re
import struct
from pathlib import Path

IMAGES = Path("docs/assets/images")
NEW_WIDTH = 2440  # 2x the old 1220 px files, for high-density screens


def _webp_canvas(path):
    """Width, height and alpha flag of an extended (VP8X) WebP file."""
    data = path.read_bytes()
    assert data[:4] == b"RIFF" and data[8:12] == b"WEBP", f"{path} is not WebP"
    assert data[12:16] == b"VP8X", f"{path} has no VP8X header (no alpha channel)"
    flags = data[20]
    width = struct.unpack("<I", data[24:27] + b"\0")[0] + 1
    height = struct.unpack("<I", data[27:30] + b"\0")[0] + 1
    return width, height, bool(flags & 0x10)


def test_home_page_shows_black_text_in_light_theme_and_white_text_in_dark():
    text = Path("docs/index.md").read_text()
    banners = dict(
        (cls, src)
        for src, cls in re.findall(
            r"!\[[^\]]*\]\(assets/images/([^)]+)\)\{: class=\"(banner-\w+)\" \}", text
        )
    )
    assert banners == {
        "banner-light": "banner-blacktext.webp",
        "banner-dark": "banner-whitetext.webp",
    }


def test_new_banners_are_transparent_webp_at_the_new_size():
    for name in ("banner-blacktext.webp", "banner-whitetext.webp"):
        width, height, alpha = _webp_canvas(IMAGES / name)
        assert (width, height) == (NEW_WIDTH, round(859 * NEW_WIDTH / 4210)), name
        assert alpha, f"{name} lost its transparent background"
        assert (IMAGES / name).stat().st_size < 150_000, f"{name} is not web-optimised"


def test_old_dark_text_banner_is_gone_and_nothing_refers_to_it():
    assert not (IMAGES / "banner-darktext.webp").exists()
    for path in Path("docs").rglob("*"):
        if path.is_file() and path.suffix in {".md", ".html", ".css", ".js", ".toml"}:
            assert "banner-darktext" not in path.read_text(), path
    assert "banner-darktext" not in Path("zensical.toml").read_text()
