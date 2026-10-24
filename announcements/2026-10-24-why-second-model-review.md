# Post 1 of 6: let a second model review your coding agent's work — 2026-10-24

Drafted by wordy for [www#80](https://github.com/radiusred/www/issues/80),
the first task of milestone M9
([radiusred/ops#37](https://github.com/radiusred/ops/issues/37)): six short
posts introducing CodeCrew to engineers who have never heard of it. This one
carries the first idea, from the page
[*AI code review by a second model*](https://codecrew.works/why/second-model-review/):
let a second model review your coding agent's work. Bluesky and X, the same
day; no LinkedIn (only the launch post, the sixth, goes there — M9-R1).

Written to the [guidelines](README.md) and the operator's rules for this
series (M9-R2): one idea, short and plain, for someone who has never heard of
CodeCrew. Nothing in either text is insider vocabulary — *pull request*,
*merge*, *model* are the reader's own words, and the two agent products the
page names as its example, Claude Code and Codex, are named rather than
alluded to. Every claim traces to the page (table below). topos is not
mentioned. Project home first and the page second, as everywhere.

The page: <https://codecrew.works/why/second-model-review/> (verified live,
HTTP 200, 2026-10-24 16:08Z, after the texts were measured and before the dry
runs; the project home <https://codecrew.works/> returned 200 at the same
time). Facts are from the page; the link card's title and description are the
project home's own `<title>` and meta description.

## Bluesky — `radiusred.bsky.social`

`announcements/bluesky-2026-10-24.txt`. **297 of 300 graphemes**, measured
with `social.bluesky.grapheme_len` on the resolved text (the README's
command). Seven facets: two links — the project home, then the page — and five
tags. The link card is the project home.

```
Who reviews your coding agent's pull requests?

Not the same model: it tends to miss what it missed the first time. Let a different one look before the merge, say Claude Code builds and Codex reviews.

[CodeCrew](https://codecrew.works/) sets that up on GitHub. [Here's how](https://codecrew.works/why/second-model-review/)

#AI #OpenSource #AIAgents #CodeReview #Programming
```

## X — `@radiusred_uk`

`announcements/x-2026-10-24.txt`. **275 of 280 weighted characters**,
measured with `social.x.weighted_len` (the README's command). Two URLs, each
weighed at 23, inline in the body with their scheme, project home first, per
the X URL Decision
([radiusred/ops#28, 2026-09-26](https://github.com/radiusred/ops/issues/28#issuecomment-5846341962)).
No emoji, no symbols outside the Latin ranges; the apostrophes are ASCII.
Three tags, plain text. The budget did not stretch to the Claude Code / Codex
example the Bluesky text carries (with it the text weighs 317), so the X copy
stops at the idea itself; the example is on the page.

```
Who reviews your coding agent's pull requests?

Not the same model: it tends to miss what it missed the first time. Let a different one look before the merge.

CodeCrew sets that up on GitHub.
https://codecrew.works/
https://codecrew.works/why/second-model-review/

#AIAgents #CodeReview #OpenSource
```

### Traceability

| claim | source |
|---|---|
| a coding agent opens pull requests | page: "One coding agent writes the change and opens a pull request" |
| not the same model: it tends to miss what it missed the first time | page: "A model checking its own work tends to miss what it missed the first time"; the reviewer instructions it quotes: "self-evaluation shares the blind spots of the work itself" |
| let a different one look before the merge | page: "A different agent, ideally running on another model or in another harness, reviews it before it merges"; "A second opinion from somewhere else is still a better bet than marking your own homework" |
| say Claude Code builds and Codex reviews | page: "So you might have Claude Code build and Codex review, or the other way round" |
| CodeCrew sets that up on GitHub | page: "CodeCrew, an extension for GitHub's gh command line, sets that up and keeps the whole exchange on GitHub"; "Who does what is a few lines in your project's settings file" |
| card title and description | project home: `<title>` "CodeCrew — Your coding agents, working as a crew on GitHub"; meta description "Give each coding agent its own GitHub App identity, so different harnesses and models can build and review each other's work, with the record kept in GitHub." |
| #OpenSource | project home's structured data: licence Apache-2.0, repository `github.com/radiusred/gh-codecrew` |

What the texts leave out, deliberately: that no review catches every bug (the
page says it; a post this short cannot carry the caveat without losing the
idea), that the reviewer starts a fresh session, and that each agent can
review under its own GitHub App. Those are the page's "three things worth
knowing" and the second of them is post 2's idea.

## Tags — how they were chosen (measured 2026-10-24)

**Bluesky.** Same method as 2026-08-27, 2026-08-30 and 2026-09-26: the
authenticated `app.bsky.feed.searchPosts`, `sort=latest`, `limit=100`,
logging in the way `social/bluesky.py` does; **hours for a tag to accumulate
its latest 100 posts**, smaller = busier. Measured 2026-10-24 16:05Z.
Forty-seven candidates: the 2026-09-26 table's twenty-two plus twenty-five
that fit this post's idea — code review, AI coding, and the products and
vendors the page names (#CodeReview, #AICodeReview, #PullRequest,
#CodeQuality, #AIAssistedCoding, #AIEngineering, #AIDevelopment, #AIDev,
#DevEx, #Developers, #Developer, #Software, #SoftwareDev, #Dev,
#MachineLearning, #GenAI, #LLMs, #Agents, #AITools, #CleanCode, #Codex,
#Claude, #Copilot, #Anthropic, #OpenAI). The measurement script lives outside
the repository, as the guidelines ask; this table is its output.

| tag | hours / 100 | | tag | hours / 100 |
|---|---:|---|---|---:|
| #AI | 0.7 | | #SoftwareDevelopment | 104.2 |
| #IndieDev | 1.1 | | #Copilot | 105.5 |
| #Tech | 3.9 | | #VibeCoding | 118.0 (99 posts ever) |
| #OpenSource | 6.9 | | #CodeReview | 156.4 |
| #Claude | 12.3 | | #LLMs | 158.1 (95 posts ever) |
| #Anthropic | 12.3 | | #Developer | 172.7 (97 posts ever) |
| #BuildInPublic | 16.8 | | #AICoding | 187.0 |
| #OpenAI | 17.7 | | #Developers | 200.3 |
| #Programming | 18.6 | | #Codex | 202.4 |
| #Agents | 19.1 | | #AIEngineering | 408.8 |
| #Dev | 19.4 | | #SoftwareDev | 653.0 |
| #LLM | 19.8 | | #AIDevelopment | 921.9 |
| #MachineLearning | 23.7 | | #CleanCode | 1632.9 |
| #AIAgents | 25.1 | | #CodeQuality | 2007.1 |
| #GenAI | 26.3 | | #AIDev | 2946.1 (88 posts ever) |
| #Coding | 26.8 | | #DevEx | 3411.1 (77 posts ever) |
| #DevOps | 27.1 | | #ReleaseNotes | 5617.3 |
| #AITools | 29.1 | | #AIAssistedCoding | 13753.3 (83 posts ever) |
| #SoloDev | 31.4 | | #AICodeReview | 16439.4 (36 posts ever) |
| #WebDev | 36.2 | | #CodeCrew | 17684.1 (14 posts ever) |
| #GitHub | 48.8 | | #PullRequest | 66885.4 (97 posts ever) |
| #Software | 49.0 | | | |
| #ClaudeCode | 51.8 | | | |
| #SoftwareEngineering | 53.3 | | | |
| #AgenticAI | 68.0 (99 posts ever) | | | |
| #DevTools | 72.1 | | | |

The prior tags track the 2026-09-26 run within noise (#AI 0.7 → 0.7,
#OpenSource 11.1 → 6.9, #AIAgents 23.4 → 25.1, #BuildInPublic 21.0 → 16.8,
#Programming 25.6 → 18.6, #ClaudeCode 56.2 → 51.8, #AICoding 335.2 → 187.0).

Chosen: **#AI** (the broad anchor, the busiest room by far), **#OpenSource**
(busy and a fact of the project), **#AIAgents** (the subject: the post is
about coding agents), **#CodeReview** (the one tag that says what the post is
about; 156 h per 100 posts is a quiet room, about fifteen posts a day, but
anyone searching it is this post's reader, and the guidelines ask for
relevance measured, not the busiest five), **#Programming** (busier than
#Coding this run, and the right general room).
Dropped: **#IndieDev** (1.1 h), a game-developer room, not ours; **#Tech**
(3.9 h), busy but about everything; **#Claude**, **#Anthropic**, **#OpenAI**,
**#Codex**, **#ClaudeCode** and **#Copilot**, vendor and product rooms — the
page says you pick the models, and the post names two products as an example,
not as its subject; **#BuildInPublic**, this post builds nothing; **#LLM** and
**#MachineLearning**, about models, where the post is about a way of working;
**#AICodeReview**, **#AIAssistedCoding** and **#PullRequest**, the obvious
tags and empty rooms, as the guidelines warn (36, 83 and 97 posts ever);
**#CodeCrew**, still no community, and the name is in the text and searchable.

**X: unmeasured, for now.** Per the guidelines' X bullet: the Bluesky method
needs a search endpoint, and on X's pay-per-use project
`GET /2/tweets/search/recent` is billed per post returned ($0.005 each at the
[pricing verified 2026-09-26](https://docs.x.com/x-api/getting-started/pricing);
a 100-post sample per candidate is $0.50, and this run's forty-seven
candidates would be $23.50, against $0.200 for the post itself). The account's
credits are for the posts of this series, not for a tag survey, so the tags
are chosen on relevance, leaning on the Bluesky table above for the same
audience. Three, to spend the budget on the sentences rather than the tags:
**#AIAgents** (the subject; busy and on topic on Bluesky, 25.1 h),
**#CodeReview** (the idea itself; quiet on Bluesky at 156.4 h but exactly the
reader), **#OpenSource** (a fact of the project; 6.9 h on Bluesky).
Considered and dropped: **#AI** (broad on X is a guess at best, and the post
is about a way of working), **#Programming** (five tags is Bluesky's rule and
the X budget is full), **#ClaudeCode** and **#Codex** (products the post gives
as an example, not its subject), **#CodeCrew** (no community yet).

## Cost

Expected **$0.200** for X: a post containing a URL, at the
[pricing verified 2026-09-26](https://docs.x.com/x-api/getting-started/pricing)
($0.015 per post, $0.200 per post containing a URL). Two URLs in one post are
one post containing a URL; the price is per post, not per link. Bluesky is
free. `uv run -m social check` was run before the dry runs (its X leg is
`GET /2/users/me`, which the 2026-09-26 console reading showed was not
billed). The billed cost is read from the X console's usage after the post,
from the operator's balance before and after, and recorded in the Result
section against the expected $0.200 (M9-R5); a different figure is raised on
radiusred/ops#37, not accepted silently.

## Commands

The measurements (from the repository root):

```sh
python3 -c "import sys; sys.path.insert(0,'.'); from social.bluesky import grapheme_len, facets; \
t=open('announcements/bluesky-2026-10-24.txt').read().strip(); r,_=facets(t); print(grapheme_len(r))"
python3 -c "import sys; sys.path.insert(0,'.'); from social.x import weighted_len; \
print(weighted_len(open('announcements/x-2026-10-24.txt').read().strip()))"
```

```
297
275
```

Credentials proved without posting, 2026-10-24 16:08Z:

```sh
uv run -m social check
```

```
bluesky: ok — radiusred.bsky.social (did:plc:tkktcn7p42upz6lu6qwtmps2)
linkedin: token revoked, expires 2026-12-23; scopes: 
linkedin: refresh token expires 2027-05-12 — re-consent before then
linkedin: administers urn:li:organization:106551263 — Radius Red / radiusred (configured)
x: ok — @radiusred_uk (2094251947972808704)
```

(stderr: `LinkedIn access token refreshed; valid to 2026-12-23`. The LinkedIn
leg reports the refreshed token as revoked with no scopes while still listing
the Page it administers; LinkedIn is not a target of this post, so it is noted
here for the launch post, which is, and not acted on.)

Two commands, one per network, because X takes its own text and no link card:

```sh
uv run -m social post --to bluesky \
    --bluesky-text-file announcements/bluesky-2026-10-24.txt \
    --link https://codecrew.works/ \
    --title "CodeCrew — Your coding agents, working as a crew on GitHub" \
    --description "Give each coding agent its own GitHub App identity, so different harnesses and models can build and review each other's work, with the record kept in GitHub." \
    --dry-run

uv run -m social post --to x --x-text-file announcements/x-2026-10-24.txt --dry-run
```

<details>
<summary>Dry-run output, verbatim (no credentials appear in it; checked)</summary>

```json
{
  "network": "bluesky",
  "dry_run": true,
  "request": {
    "method": "POST",
    "url": "https://bsky.social/xrpc/com.atproto.repo.createRecord",
    "body": {
      "repo": "<did>",
      "collection": "app.bsky.feed.post",
      "record": {
        "$type": "app.bsky.feed.post",
        "text": "Who reviews your coding agent's pull requests?\n\nNot the same model: it tends to miss what it missed the first time. Let a different one look before the merge, say Claude Code builds and Codex reviews.\n\nCodeCrew sets that up on GitHub. Here's how\n\n#AI #OpenSource #AIAgents #CodeReview #Programming",
        "createdAt": "2026-10-24T16:08:21.999Z",
        "facets": [
          {
            "index": {
              "byteStart": 202,
              "byteEnd": 210
            },
            "features": [
              {
                "$type": "app.bsky.richtext.facet#link",
                "uri": "https://codecrew.works/"
              }
            ]
          },
          {
            "index": {
              "byteStart": 235,
              "byteEnd": 245
            },
            "features": [
              {
                "$type": "app.bsky.richtext.facet#link",
                "uri": "https://codecrew.works/why/second-model-review/"
              }
            ]
          },
          {
            "index": {
              "byteStart": 247,
              "byteEnd": 250
            },
            "features": [
              {
                "$type": "app.bsky.richtext.facet#tag",
                "tag": "AI"
              }
            ]
          },
          {
            "index": {
              "byteStart": 251,
              "byteEnd": 262
            },
            "features": [
              {
                "$type": "app.bsky.richtext.facet#tag",
                "tag": "OpenSource"
              }
            ]
          },
          {
            "index": {
              "byteStart": 263,
              "byteEnd": 272
            },
            "features": [
              {
                "$type": "app.bsky.richtext.facet#tag",
                "tag": "AIAgents"
              }
            ]
          },
          {
            "index": {
              "byteStart": 273,
              "byteEnd": 284
            },
            "features": [
              {
                "$type": "app.bsky.richtext.facet#tag",
                "tag": "CodeReview"
              }
            ]
          },
          {
            "index": {
              "byteStart": 285,
              "byteEnd": 297
            },
            "features": [
              {
                "$type": "app.bsky.richtext.facet#tag",
                "tag": "Programming"
              }
            ]
          }
        ],
        "embed": {
          "$type": "app.bsky.embed.external",
          "external": {
            "uri": "https://codecrew.works/",
            "title": "CodeCrew — Your coding agents, working as a crew on GitHub",
            "description": "Give each coding agent its own GitHub App identity, so different harnesses and models can build and review each other's work, with the record kept in GitHub."
          }
        }
      }
    }
  }
}
{
  "network": "x",
  "dry_run": true,
  "request": {
    "method": "POST",
    "url": "https://api.x.com/2/tweets",
    "body": {
      "text": "Who reviews your coding agent's pull requests?\n\nNot the same model: it tends to miss what it missed the first time. Let a different one look before the merge.\n\nCodeCrew sets that up on GitHub.\nhttps://codecrew.works/\nhttps://codecrew.works/why/second-model-review/\n\n#AIAgents #CodeReview #OpenSource"
    }
  }
}
```

</details>

Nothing on stderr from either dry run. The same two commands without
`--dry-run` are what post — once each, by hand, Bluesky then X, after the
checkpoint on www#80 is resolved for each network's text (M9-R4).

## Result

_Placeholder. Filled after the checkpoint on www#80 is resolved and the posts
go out: the post URL and time for each network, the operator's X console
balance before and after, the billed X cost against the expected $0.200
(M9-R5), and the comment linking the posts on radiusred/gh-codecrew#423
(M9-R6)._
