# Radius Red Public Site

This repository is the canonical source for the Radius Red public web site, tech docs and blog.

When adding or updating blog articles, do it in this repository.

## Front Matter

Every post requires valid front matter at the top of the file:

```yaml
---
layout: default
author: Your Name
title: Post title goes here
date: YYYY-MM-DD
description: One-sentence summary, used in feed and listings
tags: [tag1, tag2, tag3]
---
```

- `layout`: Required. Set to `default` for all posts.
- `author`: Required. Author name displayed in the post byline.
- `title`: Required. Displayed as the post heading and in listings.
- `date`: Required. Sets publication order and controls visibility (see Build Visibility Controls below).
- `description`: Required. Used in feed summaries and on the blog homepage.
- `tags`: Optional. Comma-separated list of topic tags.

## Post Content

Posts should contain article content without:

- **No post title.** The template renders the title from front matter `title` field.
- **No byline or date.** The template renders publication metadata from front matter.
- **No license footer.** The template appends the Apache 2.0 license footer automatically.

Start your content with the first paragraph or section heading (`##` level 2 or deeper).

Example structure:

```markdown
---
layout: default
author: Wordy
title: Why we chose Postgres for the event store
date: 2026-04-30
description: Technical decision on data store selection for our event pipeline.
tags: [engineering, data, architecture]
---

## The Challenge

Our event pipeline requires high-fidelity, ordered writes...

## Why Postgres

We evaluated three options...
```

## Publishing Rules

- Create posts in `docs/blog/posts/` and must include a valid front matter `date`.
- The site build will handle future dated posts and ensure they do not appear until the publish date.
- Public-facing content in this repository must not reference internal systems, internal issue trackers, private repository paths, or non-public workflow tools. In practice, do not link to `RAD-*` issues, private repos, or internal orchestration platforms from site copy.

## Local Preview

- `uv sync && uv run zensical serve` should create a local site on localhost:8000

## Posting to social accounts

Announcements go out from Radius Red's own accounts — `radiusred.bsky.social`,
the LinkedIn Page `linkedin.com/company/radiusred` and `@radiusred_uk` on X —
through the `social` package in this repo. It is stdlib-only; run it with
`uv run -m social`. This section is the social runbook; `RUNBOOK.md` is about
serving the site.

**Credentials never live in this tree.** They are read from the environment
first, then from `~/.config/radiusred/social.env` (mode 0600 in a 0700
directory; `--env-file` to point elsewhere). That is the only file the tool
writes. Transitionally, when it is absent the old `~/.config/codecrew/social.env`
is still read, with one stderr line naming both paths: move the file. The
CodeCrew App keys (`*.pem`, `*.json` for `gh codecrew identity token`) stay in
`~/.config/codecrew/`; only `social.env` moves. Keys: `BSKY_HANDLE`, `BSKY_APP_PASSWORD`,
`LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`, `LINKEDIN_ACCESS_TOKEN`,
`LINKEDIN_REFRESH_TOKEN`, `LINKEDIN_ORG_URN`; optional `LINKEDIN_VERSION`
(API version, `YYYYMM`), `LINKEDIN_REDIRECT_URI`, `BSKY_PDS`. The two
`*_EXPIRES_AT` keys are maintained by the tool. For X: `X_HANDLE`
(`radiusred_uk`), `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`,
`X_ACCESS_TOKEN_SECRET` — OAuth 1.0a user context, nothing else.

**X credentials, and the pitfall.** In the X Developer Console the app's
*Keys and tokens* page shows two families. The OAuth 1.0 **Consumer Key** and
**Consumer Secret** (also called API Key and Secret) are what `X_API_KEY` and
`X_API_SECRET` take — the Consumer Key is **25 characters**. The OAuth 2.0
**Client ID** is 34 characters and is **not it**: nothing here uses OAuth 2.0,
and a Client ID in `X_API_KEY` fails every signed call with a 401. The
**Access Token** and **Access Token Secret** must be generated while signed in
as `@radiusred_uk` with the app's permissions set to **Read and write**
(regenerate them after changing the permissions — a token keeps the
permissions it was minted with). None of the four expires or rotates, so the
tool never writes an X key back to the env file. The account's developer
project is pay-per-use: [pricing as verified 2026-09-26](https://docs.x.com/x-api/getting-started/pricing)
is **$0.015 per post, $0.200 per post containing a URL**, credits bought up
front in the console (no free tier); with no credits a write is refused and
the tool says so — see `check` below.

```sh
uv run -m social check                       # prove auth without posting
uv run -m social post --to bluesky --to linkedin \
    --text-file announce.txt --link URL --title "…" --dry-run   # show the requests
uv run -m social post --to bluesky --to linkedin \
    --text-file announce.txt --link URL --title "…"             # send them
uv run -m social post --to x --x-text-file x.txt --dry-run     # X: its own text, no card
uv run -m social post --to x --x-text-file x.txt               # one gated post, by hand
uv run -m social auth linkedin               # re-consent (browser leg, human)
uv run -m social comment --urn urn:li:share:123 \
    --text-file links.txt                    # the first comment on a LinkedIn share
```

- `check` logs in to Bluesky, introspects the LinkedIn token (refreshing it
  when it has under a week left, and writing the new tokens back to the env
  file when that is where they came from), and lists the Pages the token
  administers — writing `LINKEDIN_ORG_URN` to the env file when exactly one
  Page is administered and the key is not yet set. For X it calls
  `GET /2/users/me` with the signed tokens and passes only when the account
  they belong to is `X_HANDLE` (`x: ok — @radiusred_uk (id)`); another
  account's tokens are a failure, not a warning. When the project has no
  credits, `check` and `post` print `x: FAILED — X check failed: out of
  credits — … buy credits in the X Developer Console (https://console.x.com/)`
  rather than a generic API error. That is matched positively — the
  `credits-depleted` problem type, or a title or detail saying the credits
  are depleted, exhausted, insufficient or absent — so a 402 or 403 about
  something else (a billing profile, a credit card) is reported as the API
  error it is, status included.
- `post` publishes the same text everywhere by default; Bluesky allows 300
  graphemes, so give it its own copy with `--bluesky-text-file` when the
  LinkedIn version runs longer. URLs in the text become links; on Bluesky
  `[label](url)` becomes display text carrying the link (only the label
  counts toward the 300) and `#hashtags` become tag facets — without the
  facet a tag is plain text and reaches nobody, so tag deliberately; on
  LinkedIn `#hashtags` become hashtag entities and URLs are left unescaped.
  `--link` adds a link card (Bluesky) / article (LinkedIn). Posted texts are
  kept in `announcements/`. Always `--dry-run` first —
  it prints the exact request bodies and touches no network. Output is one
  JSON line per network with the post URL.
- `post --to x` sends the text as-is (`--x-text-file` for its own copy) and
  refuses it before any network call when it is over **280 weighted
  characters**: every URL counts as 23 whatever its length, most characters
  as 1, CJK, emoji and symbols outside the Latin ranges (`€`, `•`, `⌘`) as
  2 — X's own rule. A bare domain X would autolink (`radiusred.uk`) is
  weighed as a URL too, at 23 or its literal weight, whichever is larger:
  the guard never under-counts, so it may refuse a text X would take by a
  few characters, never the reverse. Links go **inline in the body** — X has no link card and
  `--link`/`--title`/`--description` are not applied to X (a stderr line says
  so if they are passed with `--to x`); there is no reply command, per the
  standing rule in `announcements/README.md`. Write URLs with their scheme;
  a `[label](url)` is Bluesky syntax and is sent to X verbatim. `--to` is
  always explicit: there is no "all", and nothing posts to X as a side effect
  of posting elsewhere.
- `comment` posts a comment on a LinkedIn share as the Page, given the URN
  `post` printed. It is where a LinkedIn post's links go: inline URLs cost the
  post reach, so the body says "links in the first comment" and this command
  supplies it, immediately after. Comment text is plain — URLs are not escaped
  — and `--dry-run` prints the request like `post` does. The standing rules for
  announcements, including this one, are in `announcements/README.md`.
- `auth linkedin` is the re-consent playbook: it prints the consent URL,
  catches the redirect on `localhost:8765` (or `--paste` the code), exchanges
  it, and stores the tokens. Someone signed in to LinkedIn as a Page admin
  has to click through; no agent can.

Rotation calendar: LinkedIn access tokens last 60 days and refresh
themselves; the refresh token lasts a year from the last consent, after which
`auth linkedin` is needed again (`check` prints the date). Bluesky app
passwords do not expire; revoke and re-mint from the account's settings. X's
OAuth 1.0a tokens do not expire either; revoke and regenerate them in the
Developer Console (as `@radiusred_uk`, Read and write), then update the four
`X_*` keys by hand. The LinkedIn API version pinned in `social/linkedin.py`
retires after about a year — a `426 NONEXISTENT_VERSION` means bump it.
