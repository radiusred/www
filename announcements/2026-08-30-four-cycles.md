# Four-cycles article announcements — 2026-08-30

Drafted by wordy for [www#53](https://github.com/radiusred/www/issues/53), the
gated act of gh-codecrew's M7-R8. **Nothing has been posted.** The posts go out
only after the operator resolves the `cc:needs-decision` gate on that issue;
the Result section below takes the post URLs afterwards, and this file's PR
merges after that.

Written to [the guidelines](README.md), which this announcement's review
produced: plain speech for a reader who knows neither product, project home
before the article, no inline URLs on LinkedIn, a measured grapheme budget and
measured tags.

The article: <https://www.radiusred.uk/blog/posts/2026-08-30-four-cycles-on-a-real-orchestration-platform/>
(verified live, HTTP 200, 2026-08-30 19:15Z, before either text was drafted).

## Bluesky — `radiusred.bsky.social`

`announcements/bluesky-2026-08-30.txt`. **293 of 300 graphemes**, measured with
`social.bluesky.grapheme_len` on the resolved text. Eight facets: three links —
CodeCrew, Paperclip, the report — and five tags. Only the label of a
`[label](url)` counts, so the three URLs cost twenty-three graphemes between
them.

```
Can [CodeCrew](https://github.com/radiusred/gh-codecrew), an agentic coding framework, co-exist with [Paperclip](https://github.com/paperclipai/paperclip)? We ran one inside the other to see.

After a lot of work on CodeCrew: yes. Your task tracker keeps the chat, your repo keeps the record.

Read the [report](https://www.radiusred.uk/blog/posts/2026-08-30-four-cycles-on-a-real-orchestration-platform/) to find out how.

#AI #OpenSource #Programming #AIAgents #BuildInPublic
```

## LinkedIn — Radius Red Page

`announcements/linkedin-2026-08-30.txt`. **No URLs in the body and no link
card** — the body says the links are in the first comment, and the comment goes
up immediately after the post.

```
Can an agentic coding framework live inside a company-wide agent platform, or do the two fight?

We spent three days finding out. Paperclip is the open-source app teams use to manage agents at work — it hands out the work and keeps the conversation. CodeCrew is our framework for letting agents build software on plain GitHub — it keeps the record: the issues, the decisions, the reviews and the merge gates, all sitting next to the code.

So we pointed one at the other, and let a team of agents build two small games from an empty repository, with a human answering only the questions the framework is designed to escalate.

What happened:

• One whole milestone ran start to finish — build, review, tests, sign-off, merge — with no human hand on it at all, apart from the single decision it stopped to ask for.

• The expensive part was not writing the code. It was the organising: the agent doing the coordination ran up three quarters of the bill, and it was the only job on the team we had never written a description for. So we wrote it one.

• Then we let the platform hand each change straight to the agent that needed it, instead of routing everything through the organiser. Agent runs per pull request fell by two thirds, and the organiser's share of the cost fell from three quarters to a quarter.

• The answer to the original question turned out to be a boundary rather than a trick: let the platform own dispatch and discussion, let the repository own the record. Every failure we hit was one side reaching into the other's half.

Sixty-eight findings, two releases shipped while it was still running, and a job description for the agent that never had one. The write-up includes the parts that still do not work.

Links in the first comment.

Written by wordy, our documentation agent. Yes, we are agent-staffed, and the logs are public.

#ArtificialIntelligence #AIAgents #PlatformEngineering #LLMOps #OpenSource
```

### The first comment

`announcements/linkedin-2026-08-30-comment.txt`, posted seconds after the share
with `social comment --urn <the share URN the post printed>`. Project home
first, the article last.

```
Links:

CodeCrew, the framework: https://github.com/radiusred/gh-codecrew

Paperclip, the platform we ran it inside: https://github.com/paperclipai/paperclip

The full write-up, including what still does not work: https://www.radiusred.uk/blog/posts/2026-08-30-four-cycles-on-a-real-orchestration-platform/
```

`social` had no way to comment on a share, so this PR adds one:
`build_comment` / `comment_path` / `LinkedIn.comment` in `social/linkedin.py`
and a `comment` subcommand in `social/cli.py`, posting to
`POST /rest/socialActions/{share URN, URL-encoded}/comments` under the
`w_organization_social` scope the Page token already carries. A comment's
`message.text` is plain text rather than the post's "little text", so URLs
survive unescaped — which is the whole point of the first-comment slot. Four
tests cover the body shape, the encoded path, the dry run and the live call.

## Tags — how they were chosen (measured 2026-08-30)

**Bluesky.** Volume through the authenticated `app.bsky.feed.searchPosts` (the
public appview refuses an unauthenticated caller), logging in the way
`social/bluesky.py` does: **hours for a tag to accumulate its latest 100
posts**, smaller = busier. Twenty candidates:

| tag | hours / 100 | | tag | hours / 100 |
|---|---:|---|---|---:|
| #AI | 1.2 | | #GitHub | 74.5 |
| #Tech | 2.7 | | #DevTools | 81.0 |
| #OpenSource | 7.8 | | #AgenticAI | 96.7 |
| #LLM | 15.8 | | #SoftwareEngineering | 100.8 |
| #BuildInPublic | 22.0 | | #AICoding | 316.6 |
| #Programming | 22.6 | | #AIEngineering | 769.1 |
| #AIAgents | 29.0 | | #Orchestration | 2831.3 |
| #Coding | 34.8 | | #MultiAgent | 2910.6 |
| #DevOps | 45.7 | | #AutonomousAgents | 3809.4 |
| | | | #CodeCrew | 9936.7 (14 posts ever) |

The figures track 2026-08-27's within noise (#AI 1 → 1.2, #OpenSource 10 → 7.8,
#AIAgents 32 → 29, #AIEngineering 789 → 769), which is the check that the
method is stable rather than lucky.

Chosen: **#AI** (the broad anchor), **#OpenSource** (busy and exactly on
topic), **#Programming**, **#AIAgents** (the relevant niche — this article is
about agents), **#BuildInPublic** (22.0 h, twice as busy as #DevOps and the
right register for a report that publishes its own logs).
Dropped: **#DevOps**, which measured 45.7 h this time and is the weakest of the
1.0 set for a piece that is not about deployment; **#LLM**, busier at 15.8 h
but off-topic — the article is about process, not models; **#Orchestration**,
**#MultiAgent**, **#AutonomousAgents**, which read as the obvious tags for this
subject and are, measurably, empty rooms — 2,800 to 3,800 hours per 100 posts;
**#CodeCrew**, still no community, and the name is in the text and searchable.

**LinkedIn.** Follower counts are no longer exposed in the feed, so published
guide figures are the best available and they disagree by source while ranking
consistently: #ArtificialIntelligence 3M+ (SocialRails) / 11M (Writio),
#SoftwareEngineering 4.2M, #DevOps 200K+ / 890K (620K on Szabó's crawl),
#AIAgents ~320K "exploding in 2026, low competition", #PlatformEngineering
~210K "growing fast", #LLMOps ~95K "highly specific, exceptional engagement".
Both guides agree on 3–5 tags; Writio's tier rule is one Tier-1 (1M+) anchor at
most, Tier-2 (100K–1M) as the workhorses, and two or three Tier-3 (10K–100K),
which is where engagement is highest.

Chosen: **#ArtificialIntelligence** (the single Tier-1 anchor), **#AIAgents**
and **#PlatformEngineering** (Tier 2, and both literally the subject),
**#LLMOps** (Tier 3 — running agents in production and counting what each wake
costs is exactly this audience), **#OpenSource** (no follower figure in any
source consulted; kept on relevance and on the Bluesky evidence that it is the
second-busiest tag measured and on topic — stated here rather than dressed up
as a measurement).
Dropped: **#SoftwareEngineering** (4.2M) — a second Tier-1 tag against the tier
rule, and a weaker fit than the three chosen; **#DevOps**, for the same reason
as on Bluesky; **#AgenticAI**, which no source gives a figure for and which
measured 96.7 h on Bluesky.

Sources: [Writio, "Which LinkedIn hashtags get the most views in
2026"](https://writio.ai/blog/which-linkedin-hashtags-get-most-views-2026);
[SocialRails, "Best LinkedIn hashtags in
2026"](https://socialrails.com/blog/best-hashtags-for-linkedin);
[Szabó, "LinkedIn hashtags and follower
counts"](https://szabgab.com/linkedin-hashtags) (undated crawl);
[Sprout Social](https://sproutsocial.com/insights/linkedin-hashtags/) and
[Pollen](https://www.justpollen.com/blog/linkedin-hashtags) for the 3–5 rule.

## Commands

Credentials proved without posting:

```sh
uv run -m social check
```

```
bluesky: ok — radiusred.bsky.social (did:plc:tkktcn7p42upz6lu6qwtmps2)
linkedin: token active, expires 2026-10-26; scopes: r_organization_social r_organization_social_feed rw_organization_admin w_organization_social w_organization_social_feed
linkedin: refresh token expires 2027-05-12 — re-consent before then
linkedin: administers urn:li:organization:106551263 — Radius Red / radiusred (configured)
```

Three commands, because the LinkedIn post takes no link card:

```sh
uv run -m social post --to bluesky \
    --bluesky-text-file announcements/bluesky-2026-08-30.txt \
    --link https://github.com/radiusred/gh-codecrew \
    --title "CodeCrew — agent-driven software delivery, with the receipts kept in GitHub" \
    --description "Can an agentic coding framework co-exist with an agent platform? Four runs, sixty-eight findings." \
    --dry-run

uv run -m social post --to linkedin \
    --linkedin-text-file announcements/linkedin-2026-08-30.txt --dry-run

# the URN comes from the LinkedIn post's own output; then, immediately:
uv run -m social comment --urn 'urn:li:share:<from the post above>' \
    --text-file announcements/linkedin-2026-08-30-comment.txt --dry-run
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
        "text": "Can CodeCrew, an agentic coding framework, co-exist with Paperclip? We ran one inside the other to see.\n\nAfter a lot of work on CodeCrew: yes. Your task tracker keeps the chat, your repo keeps the record.\n\nRead the report to find out how.\n\n#AI #OpenSource #Programming #AIAgents #BuildInPublic",
        "createdAt": "2026-08-30T22:59:04.927Z",
        "facets": [
          {
            "index": {
              "byteStart": 4,
              "byteEnd": 12
            },
            "features": [
              {
                "$type": "app.bsky.richtext.facet#link",
                "uri": "https://github.com/radiusred/gh-codecrew"
              }
            ]
          },
          {
            "index": {
              "byteStart": 57,
              "byteEnd": 66
            },
            "features": [
              {
                "$type": "app.bsky.richtext.facet#link",
                "uri": "https://github.com/paperclipai/paperclip"
              }
            ]
          },
          {
            "index": {
              "byteStart": 215,
              "byteEnd": 221
            },
            "features": [
              {
                "$type": "app.bsky.richtext.facet#link",
                "uri": "https://www.radiusred.uk/blog/posts/2026-08-30-four-cycles-on-a-real-orchestration-platform/"
              }
            ]
          },
          {
            "index": {
              "byteStart": 240,
              "byteEnd": 243
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
              "byteStart": 244,
              "byteEnd": 255
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
              "byteStart": 256,
              "byteEnd": 268
            },
            "features": [
              {
                "$type": "app.bsky.richtext.facet#tag",
                "tag": "Programming"
              }
            ]
          },
          {
            "index": {
              "byteStart": 269,
              "byteEnd": 278
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
              "byteStart": 279,
              "byteEnd": 293
            },
            "features": [
              {
                "$type": "app.bsky.richtext.facet#tag",
                "tag": "BuildInPublic"
              }
            ]
          }
        ],
        "embed": {
          "$type": "app.bsky.embed.external",
          "external": {
            "uri": "https://github.com/radiusred/gh-codecrew",
            "title": "CodeCrew — agent-driven software delivery, with the receipts kept in GitHub",
            "description": "Can an agentic coding framework co-exist with an agent platform? Four runs, sixty-eight findings."
          }
        }
      }
    }
  }
}
{
  "network": "linkedin",
  "dry_run": true,
  "request": {
    "method": "POST",
    "url": "https://api.linkedin.com/rest/posts",
    "body": {
      "author": "urn:li:organization:106551263",
      "commentary": "Can an agentic coding framework live inside a company-wide agent platform, or do the two fight?\n\nWe spent three days finding out. Paperclip is the open-source app teams use to manage agents at work — it hands out the work and keeps the conversation. CodeCrew is our framework for letting agents build software on plain GitHub — it keeps the record: the issues, the decisions, the reviews and the merge gates, all sitting next to the code.\n\nSo we pointed one at the other, and let a team of agents build two small games from an empty repository, with a human answering only the questions the framework is designed to escalate.\n\nWhat happened:\n\n• One whole milestone ran start to finish — build, review, tests, sign-off, merge — with no human hand on it at all, apart from the single decision it stopped to ask for.\n\n• The expensive part was not writing the code. It was the organising: the agent doing the coordination ran up three quarters of the bill, and it was the only job on the team we had never written a description for. So we wrote it one.\n\n• Then we let the platform hand each change straight to the agent that needed it, instead of routing everything through the organiser. Agent runs per pull request fell by two thirds, and the organiser's share of the cost fell from three quarters to a quarter.\n\n• The answer to the original question turned out to be a boundary rather than a trick: let the platform own dispatch and discussion, let the repository own the record. Every failure we hit was one side reaching into the other's half.\n\nSixty-eight findings, two releases shipped while it was still running, and a job description for the agent that never had one. The write-up includes the parts that still do not work.\n\nLinks in the first comment.\n\nWritten by wordy, our documentation agent. Yes, we are agent-staffed, and the logs are public.\n\n{hashtag|\\#|ArtificialIntelligence} {hashtag|\\#|AIAgents} {hashtag|\\#|PlatformEngineering} {hashtag|\\#|LLMOps} {hashtag|\\#|OpenSource}",
      "visibility": "PUBLIC",
      "distribution": {
        "feedDistribution": "MAIN_FEED",
        "targetEntities": [],
        "thirdPartyDistributionChannels": []
      },
      "lifecycleState": "PUBLISHED",
      "isReshareDisabledByAuthor": false
    }
  }
}
{
  "network": "linkedin",
  "dry_run": true,
  "request": {
    "method": "POST",
    "url": "https://api.linkedin.com/rest/socialActions/urn%3Ali%3Ashare%3A%3Cfrom%20the%20post%20above%3E/comments",
    "body": {
      "actor": "urn:li:organization:106551263",
      "object": "urn:li:share:<from the post above>",
      "message": {
        "text": "Links:\n\nCodeCrew, the framework: https://github.com/radiusred/gh-codecrew\n\nPaperclip, the platform we ran it inside: https://github.com/paperclipai/paperclip\n\nThe full write-up, including what still does not work: https://www.radiusred.uk/blog/posts/2026-08-30-four-cycles-on-a-real-orchestration-platform/"
      }
    }
  }
}
```

</details>

The same three commands without `--dry-run` are what post, in that order, and
only after the gate on www#53 is resolved.

## Result

_Not posted. Awaiting the operator's `**Gate resolved:**` on
[www#53](https://github.com/radiusred/www/issues/53); the post URLs and the
comment URN land here before this PR merges._
