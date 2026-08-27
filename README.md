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

## Deploy Host Key (`WWW_VPS_HOST_KEY`)

The `CI Build` workflow pins the SSH host key of the nginx VPS via the
`WWW_VPS_HOST_KEY` repository secret rather than fetching it dynamically with
`ssh-keyscan` at deploy time. This prevents a MITM that swaps the host
fingerprint from being silently trusted by the runner.

The secret value is the verbatim public key line for the VPS, exactly as it
would appear in `~/.ssh/known_hosts`:

```
129.121.91.205 ssh-ed25519 AAAA...
```

Multiple lines are supported (e.g. ed25519 + rsa).

### Rotation procedure

Rotate `WWW_VPS_HOST_KEY` whenever the VPS host key changes (host rebuild,
distro reinstall, intentional regeneration of `/etc/ssh/ssh_host_*_key`):

1. From a trusted network, SSH to the VPS as ops and capture the new host
   key(s):
   ```bash
   ssh-keyscan -t ed25519,rsa 129.121.91.205
   ```
   Cross-check the fingerprint against the host directly
   (`ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub` on the VPS) before
   trusting the output.
2. Update the GitHub secret:
   - GitHub → repo → Settings → Secrets and variables → Actions →
     `WWW_VPS_HOST_KEY` → Update.
   - Paste the full `ssh-keyscan` output.
3. Trigger the `CI Build` workflow via `workflow_dispatch` (or merge a
   no-op docs change). The workflow fails fast if the secret is empty,
   so a missing rotation is loud.

## Posting to social accounts

Announcements go out from Radius Red's own accounts — `radiusred.bsky.social`
and the LinkedIn Page `linkedin.com/company/radiusred` — through the `social`
package in this repo. It is stdlib-only; run it with `uv run -m social`.

**Credentials never live in this tree.** They are read from the environment
first, then from `~/.config/codecrew/social.env` (mode 0600; `--env-file` to
point elsewhere). Keys: `BSKY_HANDLE`, `BSKY_APP_PASSWORD`,
`LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`, `LINKEDIN_ACCESS_TOKEN`,
`LINKEDIN_REFRESH_TOKEN`, `LINKEDIN_ORG_URN`; optional `LINKEDIN_VERSION`
(API version, `YYYYMM`), `LINKEDIN_REDIRECT_URI`, `BSKY_PDS`. The two
`*_EXPIRES_AT` keys are maintained by the tool.

```sh
uv run -m social check                       # prove auth without posting
uv run -m social post --to bluesky --to linkedin \
    --text-file announce.txt --link URL --title "…" --dry-run   # show the requests
uv run -m social post --to bluesky --to linkedin \
    --text-file announce.txt --link URL --title "…"             # send them
uv run -m social auth linkedin               # re-consent (browser leg, human)
```

- `check` logs in to Bluesky, introspects the LinkedIn token (refreshing it
  when it has under a week left, and writing the new tokens back to the env
  file when that is where they came from), and lists the Pages the token
  administers.
- `post` publishes the same text everywhere by default; Bluesky allows 300
  graphemes, so give it its own copy with `--bluesky-text-file` when the
  LinkedIn version runs longer. URLs in the text become links; `--link`
  adds a link card (Bluesky) / article (LinkedIn). Always `--dry-run` first —
  it prints the exact request bodies and touches no network. Output is one
  JSON line per network with the post URL.
- `auth linkedin` is the re-consent playbook: it prints the consent URL,
  catches the redirect on `localhost:8765` (or `--paste` the code), exchanges
  it, and stores the tokens. Someone signed in to LinkedIn as a Page admin
  has to click through; no agent can.

Rotation calendar: LinkedIn access tokens last 60 days and refresh
themselves; the refresh token lasts a year from the last consent, after which
`auth linkedin` is needed again (`check` prints the date). Bluesky app
passwords do not expire; revoke and re-mint from the account's settings. The
LinkedIn API version pinned in `social/linkedin.py` retires after about a
year — a `426 NONEXISTENT_VERSION` means bump it.
