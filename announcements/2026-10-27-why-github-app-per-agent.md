# Post 2 of 6: give each coding agent its own GitHub App identity — 2026-10-27

Drafted by wordy for [www#81](https://github.com/radiusred/www/issues/81),
the second task of milestone M9
([radiusred/ops#37](https://github.com/radiusred/ops/issues/37)): six short
posts introducing CodeCrew to engineers who have never heard of it. This one
carries the second idea, from the page
[*GitHub App for AI coding agents: one per agent*](https://codecrew.works/why/github-app-per-agent/):
give each coding agent its own GitHub App identity, instead of running them
all on one person's token. Bluesky and X, the same day; no LinkedIn (only the
launch post, the sixth, goes there — M9-R1). Post 1
([www#80](https://github.com/radiusred/www/issues/80)) went out on
2026-10-24, three days earlier.

Written to the [guidelines](README.md) and the operator's rules for this
series (M9-R2): one idea, short and plain, for someone who has never heard of
CodeCrew. Nothing in either text is insider vocabulary — *commit*, *coding
agent*, *GitHub token*, *GitHub App* are the reader's own words, and the
page's word for the agents' jobs ("role") is left on the page. The second
line aims at the register the operator set at post 1's gate: a plain
consequence in everyday words ("you can't tell"). Every claim traces to the
page (table below). topos is not mentioned. Project home first and the page
second, as everywhere.

The page: <https://codecrew.works/why/github-app-per-agent/> (verified live,
HTTP 200, 2026-10-27 23:27Z, after the drafts were measured and before the dry
runs; the project home <https://codecrew.works/> returned 200 at the same
time). Facts are from the page; the link card's title and description are the
project home's own `<title>` and meta description, as on post 1.

## Bluesky — `radiusred.bsky.social`

`announcements/bluesky-2026-10-27.txt`. **260 of 300 graphemes**, measured
with `social.bluesky.grapheme_len` on the resolved text (the README's
command). Seven facets: two links — the project home, then the page — and five
tags. The link card is the project home.

```
Who wrote that commit: you, or your coding agent?

If it uses your GitHub token, you can't tell. Give each agent its own GitHub App, and GitHub shows who did what.

[CodeCrew](https://codecrew.works/) makes each App with one command. [Here's how](https://codecrew.works/why/github-app-per-agent/)

#AI #OpenSource #AIAgents #GitHub #DevOps
```

## X — `@radiusred_uk`

`announcements/x-2026-10-27.txt`. **273 of 280 weighted characters**,
measured with `social.x.weighted_len` (the README's command). Two URLs, each
weighed at 23, inline in the body with their scheme, project home first, per
the X URL Decision
([radiusred/ops#28, 2026-09-26](https://github.com/radiusred/ops/issues/28#issuecomment-5846341962)).
No emoji, no symbols outside the Latin ranges; the apostrophes are ASCII.
Two tags, plain text (one fewer than post 1: with #OpenSource the text weighs
285). The two texts share their first two paragraphs word for word.

```
Who wrote that commit: you, or your coding agent?

If it uses your GitHub token, you can't tell. Give each agent its own GitHub App, and GitHub shows who did what.

CodeCrew makes each App with one command.
https://codecrew.works/
https://codecrew.works/why/github-app-per-agent/

#AIAgents #GitHub
```

### Traceability

| claim | source |
|---|---|
| a coding agent's commit can look like yours | page: "Many setups run every coding agent on one person's GitHub token, so every commit, comment and review looks like that person's" |
| if it uses your GitHub token, you can't tell | the same sentence: on one person's token, every commit "looks like that person's", so GitHub does not show whether the person or the agent made it |
| give each agent its own GitHub App, and GitHub shows who did what | page: "give each agent an App of its own, and GitHub shows which one did what"; under "What you see on GitHub": "One App wrote it, and a different App reviewed it" |
| CodeCrew makes each App with one command | page: "CodeCrew, an extension for GitHub's gh command line, makes one App per role with a single command"; the section heading "One command per agent" |
| card title and description (Bluesky) | project home: `<title>` "CodeCrew — Your coding agents, working as a crew on GitHub"; meta description "Give each coding agent its own GitHub App identity, so different harnesses and models can build and review each other's work, with the record kept in GitHub." |
| #AI (Bluesky), #AIAgents (both networks): the post is about AI coding agents | page: its title "GitHub App for AI coding agents: one per agent"; "A GitHub App for AI coding agents changes that: give each agent an App of its own" |
| #GitHub (both networks): the post is about GitHub | page: "give each agent an App of its own, and GitHub shows which one did what"; "CodeCrew, an extension for GitHub's gh command line"; "It sets the App up through GitHub's own creation flow" |
| #OpenSource (Bluesky): CodeCrew is open source | page: its own structured data (the `application/ld+json` in the page's head) declares the software `gh-codecrew` with `"license": "https://www.apache.org/licenses/LICENSE-2.0"` and `"codeRepository": "https://github.com/radiusred/gh-codecrew"`; the page's footer links that repository |
| #DevOps (Bluesky): the post is about running agents' access to GitHub | page: "You then install the App on your account or organisation. Each agent session then asks for a token of its own, which expires within the hour"; "The App gets only the permissions that role needs, its private key stays outside your repository"; "A required review is a branch protection rule" |

Every tag's claim traces to the linked page itself, not only to the project
home (the rule from the review of post 1,
[PR #87](https://github.com/radiusred/www/pull/87)): the four tag rows above
cite the page. The link card alone is the project home's, because the card is
the project home.

What the texts leave out, deliberately: what the one command involves (you
confirm the App in your browser, then install it on your account or
organisation — the page's own next steps, which the link covers); the
security side (narrow permissions, the private key kept outside the
repository, tokens that expire within the hour); that each App's name ends in
`[bot]`; that none of this is needed on day one; the caveat about GitHub's
required reviews; and the real pull request the page shows. Each is true and
on the page; a post this short carries one idea, and these are what the link
is for.

## Tags — how they were chosen (measured 2026-10-27)

**Bluesky.** Same method as 2026-08-27, 2026-08-30, 2026-09-26 and
2026-10-24: the authenticated `app.bsky.feed.searchPosts`, `sort=latest`,
`limit=100`, logging in the way `social/bluesky.py` does; **hours for a tag to
accumulate its latest 100 posts**, smaller = busier. Measured 2026-10-27
23:24Z. Sixty-eight candidates: the 2026-10-24 table's forty-seven plus
twenty-one that fit this post's idea — GitHub, identity and access, security,
bots and agents (#GitHubApps, #GitHubApp, #GitHubActions, #Git, #Identity,
#IAM, #Security, #InfoSec, #CyberSecurity, #AppSec, #DevSecOps,
#SupplyChainSecurity, #AISecurity, #LeastPrivilege, #AccessControl, #OAuth,
#Bots, #Automation, #AIAgent, #CodingAgents, #Auditing). The measurement
script lives outside the repository, as the guidelines ask; this table is its
output. A count in brackets is what the search returned when it was fewer
than 100: for a quiet tag that is its whole history (#GitHubApps has one post
ever), for a busy one it is the search dropping a post or two from the page
(#AI returned 99 posts covering 0.8 hours), not a small room.

| tag | hours / 100 | | tag | hours / 100 |
|---|---:|---|---|---:|
| #AI | 0.8 (99 returned) | | #Copilot | 131.4 |
| #IndieDev | 1.9 | | #Git | 135.4 |
| #Tech | 2.8 | | #VibeCoding | 146.8 |
| #CyberSecurity | 3.4 | | #AppSec | 148.4 |
| #InfoSec | 4.8 (99 returned) | | #Developers | 152.4 |
| #OpenSource | 5.8 | | #Developer | 154.4 (91 returned) |
| #Anthropic | 6.1 | | #Bots | 163.9 |
| #Security | 6.4 | | #AICoding | 184.1 |
| #Claude | 8.7 | | #LLMs | 188.4 (96 returned) |
| #LLM | 12.7 (98 returned) | | #DevSecOps | 190.3 |
| #Agents | 13.2 | | #CodeReview | 211.3 |
| #BuildInPublic | 13.3 | | #Codex | 216.7 |
| #Dev | 13.9 (99 returned) | | #AIAgent | 218.7 |
| #Programming | 14.8 | | #AIEngineering | 421.9 |
| #OpenAI | 15.5 | | #SoftwareDev | 633.4 |
| #MachineLearning | 15.6 | | #GitHubActions | 767.4 (99 returned) |
| #Coding | 17.0 (99 returned) | | #SupplyChainSecurity | 871.5 |
| #Automation | 19.5 (99 returned) | | #CodingAgents | 970.9 |
| #AIAgents | 23.6 | | #AIDevelopment | 973.5 |
| #SoloDev | 25.6 | | #CleanCode | 1628.5 (99 returned) |
| #DevOps | 26.0 | | #AccessControl | 1831.0 |
| #IAM | 31.0 | | #CodeQuality | 2086.4 |
| #WebDev | 31.1 | | #AIDev | 3013.1 (88 returned) |
| #ClaudeCode | 33.6 | | #DevEx | 3383.4 (77 returned) |
| #AITools | 36.4 | | #Auditing | 4971.9 (99 returned) |
| #GenAI | 40.4 | | #ReleaseNotes | 5696.6 |
| #Software | 41.2 | | #GitHubApps | 10405.4 (1 returned) |
| #GitHub | 51.4 (99 returned) | | #AIAssistedCoding | 13832.6 (83 returned) |
| #SoftwareEngineering | 57.4 | | #AICodeReview | 16518.7 (38 returned) |
| #AgenticAI | 62.3 | | #CodeCrew | 17763.4 (14 returned) |
| #DevTools | 68.4 | | #LeastPrivilege | 17768.5 (63 returned) |
| #Identity | 107.6 | | #GitHubApp | 60886.4 (2 returned) |
| #SoftwareDevelopment | 120.8 | | #PullRequest | 66964.7 (97 returned) |
| #AISecurity | 128.4 | | #OAuth | 159709.5 |

The prior tags track the 2026-10-24 run within noise (#AI 0.7 → 0.8,
#OpenSource 6.9 → 5.8, #AIAgents 25.1 → 23.6, #Programming 18.6 → 14.8,
#GitHub 48.8 → 51.4, #DevOps 27.1 → 26.0, #CodeReview 156.4 → 211.3).

Chosen: **#AI** (the broad anchor, the busiest room by far), **#OpenSource**
(busy, and a fact the page's own structured data states), **#AIAgents** (the post is about coding
agents), **#GitHub** (the subject: the post is about what GitHub shows, and
51.4 h per 100 posts is nearly fifty posts a day, of exactly this reader), **#DevOps** (26.0 h; the people who hand out tokens and run the bots
that use them).
Dropped: **#CyberSecurity** (3.4 h), **#InfoSec** (4.8 h) and **#Security**
(6.4 h), busy, and a shared token is a security question, but the text makes
no security claim — the page's narrow permissions and short-lived tokens are
left on the page — so a reader there would find a post about who did what,
not about risk; **#IAM** (31.0 h), the closest in vocabulary, but identity and
access management is a field of its own and the post never uses the term;
**#Programming** (14.8 h), post 1's general room, busier than #DevOps but
further from a post about who runs the agents; **#IndieDev** and **#Tech**,
as on post 1 (a game-developer room; about everything); **#Anthropic**,
**#Claude**, **#OpenAI**, **#ClaudeCode**, **#Copilot** and **#Codex**,
vendor and product rooms, and the post names no product but GitHub;
**#Automation** (19.5 h) and **#Agents** (13.2 h), broad words used well
beyond software; **#Identity** (107.6 h), **#Git** (135.4 h) and **#Bots**
(163.9 h), quieter and further from the subject than #GitHub;
**#GitHubApps**, **#GitHubApp**, **#LeastPrivilege** and **#OAuth**, the
obvious tags and empty rooms, as the guidelines warn (1, 2 and 63 posts ever;
#OAuth is the slowest room in the table); **#CodeCrew**, still no
community, and the name is in the text and searchable.

**X: unmeasured, for now.** Per the guidelines' X bullet: the Bluesky method
needs a search endpoint, and on X's pay-per-use project
`GET /2/tweets/search/recent` is billed per post returned ($0.005 each at the
[pricing verified 2026-09-26](https://docs.x.com/x-api/getting-started/pricing);
a 100-post sample per candidate is $0.50, and this run's sixty-eight
candidates would be $34.00, against $0.200 for the post itself). The
account's credits are for the posts of this series, not for a tag survey, so
the tags are chosen on relevance, leaning on the Bluesky table above for the
same audience. Two, to spend the budget on the sentences rather than the
tags: **#AIAgents** (the post is about coding agents; 23.6 h on Bluesky) and
**#GitHub** (the subject; 51.4 h on Bluesky).
Considered and dropped: **#OpenSource** (a fact of the project and post 1's
third X tag, but with it the text weighs 285 of 280, and the sentences are
the post), **#AI** (broad on X is a guess at best), **#DevOps** (five tags is
Bluesky's rule and the X budget is full), **#CodeCrew** (no community yet).

## Cost

Expected **$0.200** for X: a post containing a URL, at the
[pricing verified 2026-09-26](https://docs.x.com/x-api/getting-started/pricing)
($0.015 per post, $0.200 per post containing a URL). Two URLs in one post are
one post containing a URL; the price is per post, not per link. Bluesky is
free.

The X console's balance **before** this post is **$4.60**, the operator's
reading after post 1
([www#80, 2026-10-27 23:22Z](https://github.com/radiusred/www/issues/80#issuecomment-6456044425)).
`uv run -m social check` was run before the dry runs (its X leg is
`GET /2/users/me`, which the 2026-09-26 console reading showed was not
billed), and this task has made no other X API call, so $4.60 stands as the
before figure. The balance after the post is the operator's to
read from the console; the billed cost is the difference, recorded in the
Result section against the expected $0.200 (M9-R5). A different figure is
raised on radiusred/ops#37, not accepted silently.

## Commands

The measurements (from the repository root):

```sh
python3 -c "import sys; sys.path.insert(0,'.'); from social.bluesky import grapheme_len, facets; \
t=open('announcements/bluesky-2026-10-27.txt').read().strip(); r,_=facets(t); print(grapheme_len(r))"
python3 -c "import sys; sys.path.insert(0,'.'); from social.x import weighted_len; \
print(weighted_len(open('announcements/x-2026-10-27.txt').read().strip()))"
```

```
260
273
```

Credentials proved without posting, 2026-10-27 23:27Z:

```sh
uv run -m social check
```

```
bluesky: ok — radiusred.bsky.social (did:plc:tkktcn7p42upz6lu6qwtmps2)
linkedin: token active, expires 2026-12-23; scopes: r_organization_social r_organization_social_feed rw_organization_admin w_organization_social w_organization_social_feed
linkedin: refresh token expires 2027-05-12 — re-consent before then
linkedin: administers urn:li:organization:106551263 — Radius Red / radiusred (configured)
x: ok — @radiusred_uk (2094251947972808704)
```

(Nothing on stderr. LinkedIn is not a target of this post; its leg reads
active again, where on 2026-10-24 it read revoked after a refresh.)

Two commands, one per network, because X takes its own text and no link card.
Run 2026-10-27 23:27Z:

```sh
uv run -m social post --to bluesky \
    --bluesky-text-file announcements/bluesky-2026-10-27.txt \
    --link https://codecrew.works/ \
    --title "CodeCrew — Your coding agents, working as a crew on GitHub" \
    --description "Give each coding agent its own GitHub App identity, so different harnesses and models can build and review each other's work, with the record kept in GitHub." \
    --dry-run

uv run -m social post --to x --x-text-file announcements/x-2026-10-27.txt --dry-run
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
        "text": "Who wrote that commit: you, or your coding agent?\n\nIf it uses your GitHub token, you can't tell. Give each agent its own GitHub App, and GitHub shows who did what.\n\nCodeCrew makes each App with one command. Here's how\n\n#AI #OpenSource #AIAgents #GitHub #DevOps",
        "createdAt": "2026-10-27T23:27:28.714Z",
        "facets": [
          {
            "index": {
              "byteStart": 165,
              "byteEnd": 173
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
              "byteStart": 207,
              "byteEnd": 217
            },
            "features": [
              {
                "$type": "app.bsky.richtext.facet#link",
                "uri": "https://codecrew.works/why/github-app-per-agent/"
              }
            ]
          },
          {
            "index": {
              "byteStart": 219,
              "byteEnd": 222
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
              "byteStart": 223,
              "byteEnd": 234
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
              "byteStart": 235,
              "byteEnd": 244
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
              "byteStart": 245,
              "byteEnd": 252
            },
            "features": [
              {
                "$type": "app.bsky.richtext.facet#tag",
                "tag": "GitHub"
              }
            ]
          },
          {
            "index": {
              "byteStart": 253,
              "byteEnd": 260
            },
            "features": [
              {
                "$type": "app.bsky.richtext.facet#tag",
                "tag": "DevOps"
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
      "text": "Who wrote that commit: you, or your coding agent?\n\nIf it uses your GitHub token, you can't tell. Give each agent its own GitHub App, and GitHub shows who did what.\n\nCodeCrew makes each App with one command.\nhttps://codecrew.works/\nhttps://codecrew.works/why/github-app-per-agent/\n\n#AIAgents #GitHub"
    }
  }
}
```

</details>

Nothing on stderr from either dry run; both exited 0. The same two commands
without `--dry-run` are what post — once each, by hand, Bluesky then X, after
the checkpoint on www#81 is resolved for each network's text (M9-R4).

## Result

Posted 2026-10-27 after the operator resolved the checkpoint on www#81 with
"post them"
([**Gate resolved:**, 23:46:07Z](https://github.com/radiusred/www/issues/81#issuecomment-6456401558)),
both texts as drafted. Before sending, one dry run per network was re-run and
matched the captured one above (the files unchanged since the commit). wordy
ran the two commands above without `--dry-run`, once each, Bluesky then X:

- **Bluesky**, 23:48:35Z —
  <https://bsky.app/profile/radiusred.bsky.social/post/3myvgew36qt2c>
  (`at://did:plc:tkktcn7p42upz6lu6qwtmps2/app.bsky.feed.post/3myvgew36qt2c`).
  The CLI's output, verbatim (scanned, no credentials in it):

  ```json
  {"network": "bluesky", "uri": "at://did:plc:tkktcn7p42upz6lu6qwtmps2/app.bsky.feed.post/3myvgew36qt2c", "cid": "bafyreib2kzh5vnlx5rrjjjldsvcy2tq4rwqy7rcbg4o6qhstwe7yzfomoe", "url": "https://bsky.app/profile/radiusred.bsky.social/post/3myvgew36qt2c"}
  ```

  Verified through the public `getPosts`: author `radiusred.bsky.social`,
  text as committed, seven facets, link card on `https://codecrew.works/`.
- **X**, 23:48:38Z — <https://x.com/radiusred_uk/status/2115229217398870133>,
  id `2115229217398870133`. The CLI's output, verbatim (scanned, no
  credentials in it):

  ```json
  {"network": "x", "id": "2115229217398870133", "url": "https://x.com/radiusred_uk/status/2115229217398870133"}
  ```

  The post URL returns HTTP 200 on a plain public fetch.

Nothing on stderr from either command; both exited 0, and neither was
retried.

- **X cost: $0.200**, recorded as the expected figure for one post containing
  a URL. The balance before was $4.60; the operator cut the after-post
  console reading from this series' ceremony on 2026-10-27, so no reading
  after the post was taken and the figure is the expected one, not a billed
  one read from the console.
- **Links recorded on radiusred/gh-codecrew#423** (M9-R6 / M23-R7):
  [comment, 2026-10-27](https://github.com/radiusred/gh-codecrew/issues/423#issuecomment-6456461377).
