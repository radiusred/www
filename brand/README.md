# Brand files

The Radius Red banner. Nothing in this directory is published: the site
build reads `docs/` only.

## Originals

`originals/` holds the four banners as supplied, 4210×859 PNG:

| File | Background | Text |
|---|---|---|
| `banner-black-bg.png` | solid black | white |
| `banner-white-bg.png` | solid white | black |
| `banner-blacktext.png` | transparent | black |
| `banner-whitetext.png` | transparent | white |

## Social banners

`social/` holds the profile banners, made from `banner-black-bg.png`. The
profile picture covers the lower left on each network, so the wordmark sits
to the right of it.

| File | Size | Use |
|---|---|---|
| `social/x-header.png` | 1500×500 | X header |
| `social/bluesky-banner.png` | 3000×1000 | Bluesky banner |
| `social/linkedin-cover.png` | 4200×700 | LinkedIn Page cover |

They are uploaded by hand in each network's profile settings.

## Remaking them

```sh
uv run brand/make_banners.py
```

This writes the three social banners and the site's 1200×630 link preview,
`docs/assets/images/social-preview.png`. The sizes and the boxes the
wordmark is fitted into are at the top of the script; `tests/test_brand.py`
checks them.
