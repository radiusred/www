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

Announcements go out through the `social` package in this repo from one of
two sets of accounts, chosen with the global `--account` option (before the
verb):

- `--account radiusred`, the default — Radius Red's `radiusred.uk` on Bluesky,
  the LinkedIn Page `linkedin.com/company/radiusred` and `radiusred_uk` on X.
  Every invocation without `--account` behaves as it always has.
- `--account codecrew` — CodeCrew's own `codecrew.works` on Bluesky and
  `codecrewworks` on X. There is no CodeCrew LinkedIn Page: `--account
  codecrew` with `--to linkedin`, `comment` or `auth linkedin` refuses before
  any network call.

It is stdlib-only; run it with `uv run -m social`. This section is the social
runbook; `RUNBOOK.md` is about serving the site. The writing rules, and how a
post is drafted, approved and recorded, are in `announcements/README.md`: the
texts live in a scratch folder, not in this tree, and the post's record is one
comment with the links on the CodeCrew milestone issue.

**Credentials never live in this tree.** They are read from the environment
first, then from `~/.config/radiusred/social.env` (mode 0600 in a 0700
directory; `--env-file` to point elsewhere). That is the only file the tool
writes. Transitionally, when it is absent the old `~/.config/codecrew/social.env`
is still read, with one stderr line naming both paths: move the file. The
CodeCrew App keys (`*.pem`, `*.json` for `gh codecrew identity token`) stay in
`~/.config/codecrew/`; only `social.env` moves. Both accounts' credentials
live in that one file. Radius Red's keys: `BSKY_HANDLE`, `BSKY_APP_PASSWORD`,
`LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`, `LINKEDIN_ACCESS_TOKEN`,
`LINKEDIN_REFRESH_TOKEN`, `LINKEDIN_ORG_URN`; optional `LINKEDIN_VERSION`
(API version, `YYYYMM`), `LINKEDIN_REDIRECT_URI`, `BSKY_PDS`. The two
`*_EXPIRES_AT` keys are maintained by the tool. For X: `X_HANDLE`
(`radiusred_uk`), `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`,
`X_ACCESS_TOKEN_SECRET` — OAuth 1.0a user context, nothing else.
CodeCrew's keys are the same names with a `CODECREW_` prefix, for the keys
that are an account's own: `CODECREW_BSKY_HANDLE` (`codecrew.works`),
`CODECREW_BSKY_APP_PASSWORD`, optional `CODECREW_BSKY_PDS`, `CODECREW_X_HANDLE`
(`codecrewworks`), `CODECREW_X_ACCESS_TOKEN`, `CODECREW_X_ACCESS_TOKEN_SECRET`.
`X_API_KEY` and `X_API_SECRET` belong to the X *app*, which both accounts post
through, so they are unprefixed and shared; LinkedIn has no `CODECREW_*` keys.
The environment-over-file rule applies to every key, prefixed or not.

**X credentials, and the pitfall.** In the X Developer Console the app's
*Keys and tokens* page shows two families. The OAuth 1.0 **Consumer Key** and
**Consumer Secret** (also called API Key and Secret) are what `X_API_KEY` and
`X_API_SECRET` take — the Consumer Key is **25 characters**. The OAuth 2.0
**Client ID** is 34 characters and is **not it**: nothing here uses OAuth 2.0,
and a Client ID in `X_API_KEY` fails every signed call with a 401. The
**Access Token** and **Access Token Secret** the console generates belong to
the account that owns the app (`radiusred_uk`), minted with the app's
permissions set to **Read and write** (regenerate them after changing the
permissions — a token keeps the permissions it was minted with). The console
cannot mint tokens for a *second* account under the same app; `auth x
--account codecrew` does, through X's PIN-based OAuth 1.0a flow (below), and
stores them as `CODECREW_X_ACCESS_TOKEN` and `CODECREW_X_ACCESS_TOKEN_SECRET`.
None of these tokens expires or rotates, so apart from `auth x` the tool never
writes an X key back to the env file. The developer project is pay-per-use and
one project bills both accounts: [pricing as verified 2026-09-26](https://docs.x.com/x-api/getting-started/pricing)
is **$0.015 per post, $0.200 per post containing a URL**, and a reply is
billed like a post, so **a post plus its link reply is $0.215** ($0.015 for
the URL-free body, $0.200 for the reply carrying the URLs). Credits are bought
up front in the console (no free tier); with no credits a write is refused and
the tool says so — see `check` below.

```sh
uv run -m social check                       # prove auth without posting (Radius Red)
uv run -m social --account codecrew check    # the same for CodeCrew's accounts
uv run -m social lint --to x --text-file x.txt   # the guide's mechanical rules; post runs it too
uv run -m social post --to bluesky --to linkedin \
    --text-file announce.txt --link URL --title "…" --dry-run   # show the requests
uv run -m social post --to bluesky --to linkedin \
    --text-file announce.txt --link URL --title "…"             # send them
uv run -m social post --to x --x-text-file x.txt --dry-run     # X: its own text, no card
uv run -m social post --to x --x-text-file x.txt \
    --x-reply-file x-links.txt               # X: the post, then its link reply, two URLs out
uv run -m social --account codecrew post --to bluesky --to x \
    --text-file announce.txt --x-reply-file x-links.txt         # as CodeCrew
uv run -m social post --to x --reply-to 1234567890 --text-file reply.txt      # reply on X
uv run -m social post --to bluesky \
    --reply-to https://bsky.app/profile/someone.example/post/3kabc \
    --text-file reply.txt                    # reply on Bluesky (at:// URI or bsky.app URL)
uv run -m social --account codecrew auth x   # mint CodeCrew's X tokens (PIN flow, human)
uv run -m social auth linkedin               # re-consent (browser leg, human)
uv run -m social comment --urn urn:li:share:123 \
    --text-file links.txt                    # the first comment on a LinkedIn share
```

- `check` logs in to Bluesky and passes only when the session's handle is the
  account's configured one (`BSKY_HANDLE`, or `CODECREW_BSKY_HANDLE` under
  `--account codecrew`); introspects the LinkedIn token (refreshing it
  when it has under a week left, and writing the new tokens back to the env
  file when that is where they came from), and lists the Pages the token
  administers — writing `LINKEDIN_ORG_URN` to the env file when exactly one
  Page is administered and the key is not yet set; under `--account codecrew`
  LinkedIn is reported as skipped. For X it calls
  `GET /2/users/me` with the signed tokens and passes only when the account
  they belong to is the account's handle key (`x: ok — @radiusred_uk (id)`,
  or `@codecrewworks` for CodeCrew); another account's tokens — Radius Red's
  pasted under the `CODECREW_*` names, say — are a failure, not a warning.
  When the project has no
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
  `--link` adds a link card (Bluesky) / article (LinkedIn). Always `--dry-run`
  first — it prints the exact request bodies and touches no network. Output is
  one JSON line per network with the post URL.
- `post --to x` sends the text as-is (`--x-text-file` for its own copy) and
  refuses it before any network call when it is over **280 weighted
  characters**: every URL counts as 23 whatever its length, most characters
  as 1, CJK, emoji and symbols outside the Latin ranges (`€`, `•`, `⌘`) as
  2 — X's own rule. A bare domain X would autolink (`radiusred.uk`) is
  weighed as a URL too, at 23 or its literal weight, whichever is larger:
  the guard never under-counts, so it may refuse a text X would take by a
  few characters, never the reverse. X has no link card:
  `--link`/`--title`/`--description` are not applied to X (a stderr line says
  so if they are passed with `--to x`). **Links go in a reply**, per
  `announcements/README.md`: `--x-reply-file <file>` posts the body, then the
  file's text as a reply to it, and prints two JSON lines, one URL each. The
  body must then carry no URL — not a scheme URL, not a bare domain X would
  autolink — and `lint` refuses one before any network call; the reply's
  length is checked up front too. If the body posts and the reply fails, the
  body's URL is printed as usual, the reply's line carries the error, and a
  stderr line gives the exact `--reply-to` command to retry the reply alone.
  Write URLs with their scheme; a `[label](url)` is Bluesky syntax and is
  sent to X verbatim. `--to` is always explicit: there is no "all", and
  nothing posts to X as a side effect of posting elsewhere.
- `post --reply-to <ref>` publishes the text as a reply, on **one** network
  per invocation (`--to bluesky` or `--to x`; never LinkedIn). On X the ref is
  a post ID or an `x.com`/`twitter.com` status URL, and the body carries
  `reply.in_reply_to_tweet_id`. On Bluesky it is a post's `at://` URI or its
  `bsky.app` URL (a handle in the URL is resolved to a DID first); the tool
  fetches the post through the PDS (`app.bsky.feed.getPosts`) so the record's
  `reply.parent` is that post and `reply.root` is the thread it belongs to —
  the post itself when it is top-level, its own root when it is a reply —
  both with `uri` and `cid`. A ref for the wrong network is a usage error
  before any call. `--dry-run` fetches nothing and prints the Bluesky refs as
  placeholders. A reply on X is billed like a post ($0.015, or $0.200 with a
  URL).
- `lint --to <network>` (`--text` or `--text-file`) checks a text against the
  guide's mechanical rules — an em dash, a first sentence that is a question,
  the banned words, a call-to-action label opening a sentence, a line or a
  Bluesky link label, the network's hashtag limit, a URL in an X body, emoji,
  and the "agent staffed, human moderated" form — printing each failure with
  the rule and the fragment, exit 1 on any; `--reply` marks a reply, which
  may carry the link. `post` runs it on every text before any network call,
  dry run included: each network's body (as a reply when `--reply-to` is
  given) and the `--x-reply-file` text as a reply; it refuses a failing text;
  `--skip-lint` sends a text the operator has approved as it stands, with one
  stderr line saying lint was skipped. The rules, and the list, are in
  `announcements/README.md` and `social/lint.py`.
- `comment` posts a comment on a LinkedIn share as the Page, given the URN
  `post` printed. It is where a LinkedIn post's links go: inline URLs cost the
  post reach, so the body says "links in the first comment" and this command
  supplies it, immediately after. Comment text is plain — URLs are not escaped
  — and `--dry-run` prints the request like `post` does. The standing rules for
  announcements, including this one, are in `announcements/README.md`.
- `auth x [--account codecrew]` mints X user tokens for the account under
  the shared app, by X's PIN-based ("out-of-band") OAuth 1.0a flow: it
  requests a temporary token, prints the authorize URL, and waits for the
  PIN. Someone signed in to X **as that account** opens the URL, approves the
  app and types the PIN back; the tool exchanges it, checks the tokens belong
  to the account's handle key (`CODECREW_X_HANDLE`, which must be set first —
  tokens for another account are refused and nothing is stored), and persists
  them under the account's names. No token or secret is ever printed. Needs
  `X_API_KEY`/`X_API_SECRET` and, on the app's *User authentication settings*,
  OAuth 1.0a enabled with Read and write; the callback can be anything since
  the flow uses the PIN. It reads the PIN from the terminal, so run it from a
  shell: when stdin is not a terminal (an agent's non-interactive command,
  say) it exits 1 with one line saying so, before requesting any token.
- `auth linkedin` is the re-consent playbook: it prints the consent URL,
  catches the redirect on `localhost:8765` (or `--paste` the code), exchanges
  it, and stores the tokens. Someone signed in to LinkedIn as a Page admin
  has to click through; no agent can. `--paste` reads the code from the
  terminal and, like `auth x`, exits 1 with one line when stdin is not one.

Rotation calendar: LinkedIn access tokens last 60 days and refresh
themselves; the refresh token lasts a year from the last consent, after which
`auth linkedin` is needed again (`check` prints the date). Bluesky app
passwords do not expire; revoke and re-mint from each account's settings. X's
OAuth 1.0a tokens do not expire either; to replace them, revoke them in the
Developer Console (Radius Red's: regenerate there, as `radiusred_uk`, Read and
write, then update `X_ACCESS_TOKEN` and `X_ACCESS_TOKEN_SECRET` by hand) and
run `auth x --account codecrew` for CodeCrew's. The LinkedIn API version
pinned in `social/linkedin.py` retires after about a year — a
`426 NONEXISTENT_VERSION` means bump it.
