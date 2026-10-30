# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow>=11"]
# ///
"""Make the link preview and the social banner files from the black original.

Run from the repository root:

    uv run brand/make_banners.py

The banner is scaled to fit a box on a canvas of the target size, filled with
the original's own background colour. Each social box keeps the wordmark clear
of the lower-left corner, where the network puts the profile picture (M11-R4).
"""

from pathlib import Path

from PIL import Image, ImageChops, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "brand/originals/banner-black-bg.png"

BACKGROUND = (17, 17, 17)
# The radar runs off the original's top and bottom edges. On a taller canvas
# that shows as a hard line, so these rows fade into the background.
FADE_ROWS = 120
# The radar is never brighter than 139 in any channel; the lettering is at
# least 170. Pixels at or above this keep full strength through the fade.
LETTERING = 170

# name: (canvas size, box (left, top, right, bottom) the banner is fitted into)
OUTPUTS = {
    "docs/assets/images/social-preview.png": ((1200, 630), (60, 0, 1140, 630)),
    "brand/social/x-header.png": ((1500, 500), (420, 40, 1460, 460)),
    "brand/social/bluesky-banner.png": ((3000, 1000), (600, 100, 2900, 900)),
    "brand/social/linkedin-cover.png": ((4200, 700), (700, 130, 4100, 570)),
}


def _faded(src: Image.Image) -> Image.Image:
    width, height = src.size
    r, g, b = src.split()
    brightest = ImageChops.lighter(ImageChops.lighter(r, g), b)
    lettering = brightest.point(lambda v: 255 if v >= LETTERING else 0)
    lettering = lettering.filter(ImageFilter.MaxFilter(7))  # keep anti-aliased edges

    def ramp(y: int) -> int:
        d = min(y, height - 1 - y)
        if d >= FADE_ROWS:
            return 255
        t = d / FADE_ROWS
        return round(255 * t * t * (3 - 2 * t))

    edges = Image.new("L", (1, height))
    edges.putdata([ramp(y) for y in range(height)])
    mask = ImageChops.lighter(edges.resize((width, height)), lettering)
    return Image.composite(src, Image.new("RGB", src.size, BACKGROUND), mask)


def _place(banner: Image.Image, size, box) -> Image.Image:
    left, top, right, bottom = box
    w = right - left
    h = round(w * banner.height / banner.width)
    if h > bottom - top:
        h = bottom - top
        w = round(h * banner.width / banner.height)
    canvas = Image.new("RGB", size, BACKGROUND)
    scaled = banner.resize((w, h), Image.LANCZOS)
    canvas.paste(scaled, (left + (right - left - w) // 2, top + (bottom - top - h) // 2))
    return canvas


def main() -> None:
    banner = _faded(Image.open(SOURCE).convert("RGB"))
    for name, (size, box) in OUTPUTS.items():
        path = ROOT / name
        path.parent.mkdir(parents=True, exist_ok=True)
        _place(banner, size, box).save(path, optimize=True)
        print(f"{name} {size[0]}x{size[1]}")


if __name__ == "__main__":
    main()
