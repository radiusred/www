# Four-cycles article announcements — 2026-08-30

Drafted by wordy for [www#53](https://github.com/radiusred/www/issues/53), the
gated act of gh-codecrew's M7-R8. **Nothing has been posted.** The posts go out
only after the operator resolves the `cc:needs-decision` gate on that issue;
the Result section below takes the post URLs afterwards, and this file's PR
merges after that, as the 1.0 announcement did.

The article: <https://www.radiusred.uk/blog/posts/2026-08-30-four-cycles-on-a-real-orchestration-platform/>
(verified live, HTTP 200, 2026-08-30 19:15Z, before either text was drafted).

Links go to the project home first, the article second — the operator's
standing instruction from [www#47](https://github.com/radiusred/www/issues/47).

## Bluesky — `radiusred.bsky.social`

`announcements/bluesky-2026-08-30.txt`. **294 of 300 graphemes**, measured with
`social.bluesky.grapheme_len` on the resolved text, not by eye: only the label
of a `[label](url)` counts, so the article link costs eleven graphemes rather
than ninety-six. Seven facets — two links, five tags.

```
We let an orchestration platform drive CodeCrew: 4 cycles, 5 milestones, 68 findings — and our biggest cost was the one role with no contract. So we wrote it one.

Project: https://github.com/radiusred/gh-codecrew
Field report: [four cycles](https://www.radiusred.uk/blog/posts/2026-08-30-four-cycles-on-a-real-orchestration-platform/)

#AI #OpenSource #Programming #AIAgents #BuildInPublic
```

## LinkedIn — Radius Red Page

`announcements/linkedin-2026-08-30.txt`. The link card is the project home;
`#tags` become hashtag entities.

```
We pointed an orchestration platform at our own framework and let it drive.

Over four cycles at the end of August, a company of agents running on Paperclip drove CodeCrew — Radius Red's framework for agent-driven software delivery on plain GitHub — through five milestones on two throwaway game repositories. From the second cycle on, the operator answered protocol gates and nothing else; every other stall was left standing and logged with a clock on it.

Project home: https://github.com/radiusred/gh-codecrew

Four things came out of it, with the numbers attached:

• The third cycle ran from task to review to milestone close with zero operator touches that were not gates. That is the framework's stated goal, happening for real rather than on a slide.

• Coordination was the cost, not the building. In that cycle the coordination layer was 75% of the bill — and it was the one role we had never written a contract for. So we wrote it one.

• In the fourth cycle we took the coordinator out of the transitions and routed GitHub's events straight to the seats. Runs per pull request fell by two thirds, and the coordinator's share of the bill went from three quarters to a quarter.

• The separation that made every failure legible: the platform keeps dispatch and discussion, CodeCrew owns the record and routing. Every stall in the run was one side trying to own the other's half.

Sixty-eight numbered findings, two point releases shipped while the run was still going, and a fifth seat in the next release. Paperclip is the platform that made the experiment possible; where it surprised us, that is in the findings too.

The full field report, including the section on what is still not solved: https://www.radiusred.uk/blog/posts/2026-08-30-four-cycles-on-a-real-orchestration-platform/

Written by wordy, the crew's doc-synthesizer seat. Yes, we are agent-staffed; the logs are public.

#ArtificialIntelligence #AIAgents #PlatformEngineering #LLMOps #OpenSource
```

## Tags — how they were chosen (measured 2026-08-30)

The operator asked for research rather than instinct (www#47, PR #50). Same
method as the 1.0 announcement, so the two runs are comparable.

**Bluesky.** Discovery is keyed on tags — custom feeds and search match them —
so volume is what matters. Measured through the authenticated
`app.bsky.feed.searchPosts` (the public appview refuses an unauthenticated
caller), logging in the way `social/bluesky.py` does: **hours for a tag to
accumulate its latest 100 posts**, smaller = busier. Twenty candidates:

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
right register for a field report that publishes its own logs).
Dropped: **#DevOps**, which measured 45.7 h this time and is the weakest of the
1.0 set for a piece that is not about deployment; **#LLM**, busier at 15.8 h
but off-topic — the article is about process, not models; **#Orchestration**,
**#MultiAgent**, **#AutonomousAgents**, which read as the obvious tags for this
subject and are, measurably, empty rooms — 2,800 to 3,800 hours per 100 posts;
**#CodeCrew**, still no community, and the name is in the text and searchable.

**LinkedIn.** LinkedIn no longer exposes hashtag follower counts in the feed,
so published guide figures are the best available and they disagree by source
while ranking consistently: #ArtificialIntelligence 3M+ (SocialRails) / 11M
(Writio), #SoftwareEngineering 4.2M, #DevOps 200K+ / 890K (620K on Szabó's
crawl), #AIAgents ~320K "exploding in 2026, low competition",
#PlatformEngineering ~210K "growing fast", #LLMOps ~95K "highly specific,
exceptional engagement". Both guides agree on 3–5 tags per post; Writio's tier
rule is one Tier-1 (1M+) anchor at most, Tier-2 (100K–1M) as the workhorses,
and two or three Tier-3 (10K–100K), which is where engagement is highest.

Chosen: **#ArtificialIntelligence** (the single Tier-1 anchor),
**#AIAgents** and **#PlatformEngineering** (Tier 2, and both literally the
subject), **#LLMOps** (Tier 3 — running agents in production and counting what
each wake costs is exactly this audience), **#OpenSource** (no follower figure
in any source consulted; kept on relevance and on the Bluesky evidence that it
is the second-busiest tag measured and on topic — stated here rather than
dressed up as a measurement).
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

The exact requests, printed and sent nowhere:

```sh
uv run -m social post --to bluesky --to linkedin \
    --bluesky-text-file announcements/bluesky-2026-08-30.txt \
    --linkedin-text-file announcements/linkedin-2026-08-30.txt \
    --link https://github.com/radiusred/gh-codecrew \
    --title "CodeCrew — agent-driven software delivery, with the receipts kept in GitHub" \
    --description "Four cycles of an orchestration platform driving the crew: the numbers, the findings, and the seat they turned up." \
    --dry-run
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
        "text": "We let an orchestration platform drive CodeCrew: 4 cycles, 5 milestones, 68 findings — and our biggest cost was the one role with no contract. So we wrote it one.\n\nProject: https://github.com/radiusred/gh-codecrew\nField report: four cycles\n\n#AI #OpenSource #Programming #AIAgents #BuildInPublic",
        "createdAt": "2026-08-30T19:20:54.415Z",
        "facets": [
          {
            "index": {
              "byteStart": 175,
              "byteEnd": 215
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
              "byteStart": 230,
              "byteEnd": 241
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
              "byteStart": 243,
              "byteEnd": 246
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
              "byteStart": 247,
              "byteEnd": 258
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
              "byteStart": 259,
              "byteEnd": 271
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
              "byteStart": 272,
              "byteEnd": 281
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
              "byteStart": 282,
              "byteEnd": 296
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
            "description": "Four cycles of an orchestration platform driving the crew: the numbers, the findings, and the seat they turned up."
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
      "commentary": "We pointed an orchestration platform at our own framework and let it drive.\n\nOver four cycles at the end of August, a company of agents running on Paperclip drove CodeCrew — Radius Red's framework for agent-driven software delivery on plain GitHub — through five milestones on two throwaway game repositories. From the second cycle on, the operator answered protocol gates and nothing else; every other stall was left standing and logged with a clock on it.\n\nProject home: https://github.com/radiusred/gh-codecrew\n\nFour things came out of it, with the numbers attached:\n\n• The third cycle ran from task to review to milestone close with zero operator touches that were not gates. That is the framework's stated goal, happening for real rather than on a slide.\n\n• Coordination was the cost, not the building. In that cycle the coordination layer was 75% of the bill — and it was the one role we had never written a contract for. So we wrote it one.\n\n• In the fourth cycle we took the coordinator out of the transitions and routed GitHub's events straight to the seats. Runs per pull request fell by two thirds, and the coordinator's share of the bill went from three quarters to a quarter.\n\n• The separation that made every failure legible: the platform keeps dispatch and discussion, CodeCrew owns the record and routing. Every stall in the run was one side trying to own the other's half.\n\nSixty-eight numbered findings, two point releases shipped while the run was still going, and a fifth seat in the next release. Paperclip is the platform that made the experiment possible; where it surprised us, that is in the findings too.\n\nThe full field report, including the section on what is still not solved: https://www.radiusred.uk/blog/posts/2026-08-30-four-cycles-on-a-real-orchestration-platform/\n\nWritten by wordy, the crew's doc-synthesizer seat. Yes, we are agent-staffed; the logs are public.\n\n{hashtag|\\#|ArtificialIntelligence} {hashtag|\\#|AIAgents} {hashtag|\\#|PlatformEngineering} {hashtag|\\#|LLMOps} {hashtag|\\#|OpenSource}",
      "visibility": "PUBLIC",
      "distribution": {
        "feedDistribution": "MAIN_FEED",
        "targetEntities": [],
        "thirdPartyDistributionChannels": []
      },
      "lifecycleState": "PUBLISHED",
      "isReshareDisabledByAuthor": false,
      "content": {
        "article": {
          "source": "https://github.com/radiusred/gh-codecrew",
          "title": "CodeCrew — agent-driven software delivery, with the receipts kept in GitHub",
          "description": "Four cycles of an orchestration platform driving the crew: the numbers, the findings, and the seat they turned up."
        }
      }
    }
  }
}
```

</details>

The same command without `--dry-run` is what posts, and only after the gate on
www#53 is resolved.

## Result

_Not posted. Awaiting the operator's `**Gate resolved:**` on
[www#53](https://github.com/radiusred/www/issues/53); the post URLs land here
before this PR merges._
