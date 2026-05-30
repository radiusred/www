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
title: Why we chose Dukascopy for market data
date: 2026-04-30
description: Technical decision on data provider selection for tradedesk.
tags: [tradedesk, data, architecture]
---

## The Challenge

Systematic trading requires high-fidelity market data...

## Why Dukascopy

We evaluated three providers...
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
