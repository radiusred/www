# X introduction post — 2026-09-26

Drafted by wordy for [www#76](https://github.com/radiusred/www/issues/76),
the one task of milestone M8
([radiusred/ops#34](https://github.com/radiusred/ops/issues/34)): the first
post on `@radiusred_uk`, introducing Radius Red and CodeCrew to an engineer
who has never heard of either. It is not tied to an article, so it carries one
link, the project home, per the guideline's "project home first".

Written to the [guidelines](README.md): plain speech, no insider vocabulary
(the words it does use — *crew*, *identity*, *the record* — are the ones the
project home itself uses), GitHub named rather than alluded to, the URL inline
in the body with its scheme per the X URL Decision
([radiusred/ops#28, 2026-09-26](https://github.com/radiusred/ops/issues/28#issuecomment-5846341962)),
tags as plain text, and a measured budget. The coordinator's draft, at 274
weighted characters, was checked claim by claim (table below) and stands as
drafted: nothing in it needed correcting, and the six characters of headroom
did not buy a clearer sentence.

The project home: <https://codecrew.works/> (verified live, HTTP 200,
2026-09-26 ~16:33Z, after the text was measured and before it was committed;
<https://www.radiusred.uk/about/> returned 200 at the same time). Facts are
from the project home, the
[gh-codecrew README](https://github.com/radiusred/gh-codecrew/blob/main/README.md)
and the company's own About page.

## X — `@radiusred_uk`

`announcements/x-2026-09-26.txt`. **274 of 280 weighted characters**,
measured with `social.x.weighted_len` (the README's command). One URL,
weighed at 23 — its literal length happens to be 23 as well, so the weighted
and the plain count coincide. No emoji, no symbols outside the Latin ranges;
the apostrophe is the ASCII one. Three tags, plain text.

```
We're Radius Red, a company staffed by AI agents.

CodeCrew is how they build: a crew of coding agents on plain GitHub, each with its own identity. One builds, another reviews, and the record stays in issues and PRs.

https://codecrew.works/

#AIAgents #DevTools #OpenSource
```

### Traceability

| claim | source |
|---|---|
| Radius Red is a company staffed by AI agents | [radiusred.uk/about](https://www.radiusred.uk/about/): "engineering ventures staffed by AI agents under human governance"; "gh-codecrew — the framework our agent crew itself runs on" |
| CodeCrew is how they build | the same page: "gh-codecrew — the framework our agent crew itself runs on"; README: the `roles:` table of "this repository's own `.codecrew/config.yml`", its seats held by the radiusred-cody, -checky, -testy and -wordy Apps |
| a crew of coding agents on plain GitHub | project home: "Your coding agents, working as a crew on GitHub"; README: "There is no server, no database and no state files" |
| each with its own identity | project home: "CodeCrew gives each of your coding agents a GitHub App identity of its own" |
| one builds, another reviews | project home: "One agent builds. Another checks the work."; README: "an approving review from whoever holds the reviewer seat" |
| the record stays in issues and PRs | README: "Project state lives in GitHub and nowhere else: a milestone is an issue, a task is an issue with a plan in its body, decisions and deviations are comments … and the work of a task is a branch and a PR" |
| #OpenSource | Apache-2.0 on the project home's structured data and the repository's licence; About page: "the open-source tools produced by our engineering work" |

## Tags — best guesses, unmeasured

Per the guideline's X bullet, these are **not measured**. The Bluesky method
needs a search endpoint, and on X's pay-per-use project
`GET /2/tweets/search/recent` is billed per post returned ($0.005 each at the
[pricing verified 2026-09-26](https://docs.x.com/x-api/getting-started/pricing):
a 100-post sample per candidate is $0.50, and a candidate list the size of the
Bluesky one, twenty-two tags, would be $11). The account had no credits when
the transport was added (M7-R4), and its first credits are for this post, not
for a tag survey; the survey is costed here so it can be run once the operator
chooses to fund it. Until then the tags are chosen on relevance, leaning on the
[Bluesky table measured 2026-09-26](2026-09-26-protocol-2-1.md#tags--how-they-were-chosen-measured-2026-09-26)
for the same audience.

Chosen, three, to spend the budget on the sentence rather than the tags:
**#AIAgents** (the subject; on Bluesky the tag was busy and on topic, 23.4 h
per 100 posts), **#DevTools** (the audience M8-R1 names — engineers who might
run it — and a tool is what CodeCrew is; 55.9 h on Bluesky, a quieter but
better-fitting room), **#OpenSource** (a fact of the project, and the tag's
Bluesky room was busy at 11.1 h).
Considered and dropped: **#AI** (the busiest room on Bluesky at 0.7 h, but
the post is about a way of working, not about models, and a broad tag on X is
a guess at best), **#BuildInPublic** (this post announces no build),
**#Programming** (nothing in it is about code), **#GitHub** (a product tag,
and the product is already named in the body), **#CodeCrew** (no community
yet; the name is in the text and searchable).

## Cost

Expected **$0.200**: a post containing a URL, at the
[pricing verified 2026-09-26](https://docs.x.com/x-api/getting-started/pricing)
($0.015 per post, $0.200 per post containing a URL). The same page lists
reads: *User: Read $0.010 per resource*. That is why `uv run -m social check`
was **not** run for this announcement: its X leg is `GET /2/users/me`, a
billed user read, and `--dry-run` proves the request body without touching
the network. The one live call is the post itself.

The billed cost is checked against the console's usage after the post, per
the X URL Decision and M8-R4: the operator reads the credit balance before and
after, and the difference is recorded in the Result section. A figure other
than $0.200 is raised on the milestone, not accepted silently.

## Commands

The measurement (from the repository root):

```sh
uv run python -c "from social.x import weighted_len; \
print(weighted_len(open('announcements/x-2026-09-26.txt').read().strip()))"
```

```
274
```

The dry run, one command because X takes its own text and no link card:

```sh
uv run -m social post --to x --x-text-file announcements/x-2026-09-26.txt --dry-run
```

<details>
<summary>Dry-run output, verbatim (no credentials appear in it; checked)</summary>

```json
{
  "network": "x",
  "dry_run": true,
  "request": {
    "method": "POST",
    "url": "https://api.x.com/2/tweets",
    "body": {
      "text": "We're Radius Red, a company staffed by AI agents.\n\nCodeCrew is how they build: a crew of coding agents on plain GitHub, each with its own identity. One builds, another reviews, and the record stays in issues and PRs.\n\nhttps://codecrew.works/\n\n#AIAgents #DevTools #OpenSource"
    }
  }
}
```

</details>

Nothing on stderr. The same command without `--dry-run` is what posts — once,
by hand, after the checkpoint on www#76 is resolved.

## Result

_Placeholder. Filled after the operator resolves the checkpoint on
[www#76](https://github.com/radiusred/www/issues/76) and the post goes out:
the post URL and time, the verification, and the billed cost read from the
X console's usage against the expected $0.200 (M8-R4)._
