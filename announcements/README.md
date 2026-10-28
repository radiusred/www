# Announcement guide

How a post is written, checked and sent from our social accounts through the
`social` package in this repo. The rules are the operator's, reviewed on
2026-10-28 because the posts so far read as machine-written. They apply to
every post until they are changed here.

Posts are managed outside the repository (operator's Decision on
[radiusred/ops#37](https://github.com/radiusred/ops/issues/37#issuecomment-6457195042)):
draft the texts in a scratch folder, one per network, and keep nothing in this
tree. The commands are in the main README, "Posting to social accounts".

## Accounts

- **Radius Red**: Bluesky `radiusred.bsky.social`, X `radiusred_uk`, the
  LinkedIn Page `linkedin.com/company/radiusred`. The CLI's default
  (`--account radiusred`). Radius Red's own news.
- **CodeCrew**: Bluesky `codecrew.works`, X `codecrewworks`
  (`--account codecrew`). CodeCrew news goes out from these: releases,
  milestone closes, merged work, the `why/` pages, within the scope below.

## What CodeCrew posts about

CodeCrew's accounts post about gh-codecrew itself or how it is used: the
CLI, the protocol, the role contracts, releases, and the docs a user follows.
Never a change that only touches the codecrew.works website: styling, layout,
accessibility fixes, the homepage. CodeCrew's users don't need to know that a
tab stop was fixed or a colour changed (the operator's Decision on
[radiusred/gh-codecrew#423](https://github.com/radiusred/gh-codecrew/issues/423#issuecomment-6469436459)).
A website change that ships alongside gh-codecrew work is not the post's
subject; the gh-codecrew work is.

## The voice

Write like a developer telling another developer what shipped. Plain,
specific, a little dry. "We" is fine. Normal sentences, not fragments.

Write for someone who has never heard of us. No insider vocabulary: not
"cycles", not "protocol gates", not "seats" or "the coordination layer". A
reader who knows neither our product nor the platform we are talking about
should still understand what happened. Name the other products involved; do
not allude to them. The detail belongs in the linked page. Claims stay
factual and traceable to the record; plain does not mean loose.

### Do

- Lead with the thing itself, by name: "gh-codecrew v2.1.2 is out."
- Give one concrete detail a developer would care about: a number, a
  command, the bug it fixes, what the reviewer caught.
- Use real numbers from the record, never rounded up.
- Links: a plain label or the bare URL. On X, the link goes in a reply.

### Don't (the tells in our posts so far)

1. Open with a rhetorical question. ("Who reviews your coding agent's pull
   requests?")
2. Set up a line just to knock it down. ("Usually it listens. Usually isn't
   good enough." "Fittingly, ...")
3. Write slogan antitheses. ("Your task tracker keeps the chat, your repo
   keeps the record." "lets small work stay small")
4. List three things for rhythm. If there really are three things, list
   them.
5. Use call-to-action labels: `What changed`, `Here's how`, `Find out`,
   `Read the … to find out`, `Learn more`, `Check it out`, `See how`, `Click`,
   `Link in`. Lint refuses each of these where it opens a sentence, a line or
   a Bluesky link label; the same words inside a sentence ("the reviewer
   found what changed in the diff") are yours to judge.
6. Use em dashes or colon reveals. ("puts that rule in code: the merge
   command ...")
7. Make a point of being agent staffed in every post, or make a joke of it.
   ("Yes, we are agent-staffed.") Mention it now and then, in passing, and
   always in the full form: "agent staffed, human moderated" (no hyphen).
8. Use these words: `seamless`, `robust`, `leverage`, `unlock`,
   `game-changer`, `delve`, `elevate`, `empower`, `journey`, `landscape`,
   `supercharge`, `here's the thing`, `the best part`, `excited to announce`,
   `thrilled to announce`.
9. Hashtags: none on X. On Bluesky, at most two, and specific (#CodeReview,
   not #AI #Programming).
10. Emoji.

### Before and after

Before: "You can tell your coding agent not to merge until the tests pass and
the work is reviewed. Usually it listens. [CodeCrew] puts that rule in code:
the merge command checks first, and refuses if anything is missing. [Here's
how]"

After: "CodeCrew's merge command won't run until CI has passed, a second
model has approved the PR, and nobody has an open question on the task. We
used to put that rule in the agent's instructions. It mostly followed them."
(Reply: https://codecrew.works/why/gates-in-code/)

## Hashtags

- **X: none.** They make a post look like spam and cost it reach.
- **Bluesky: at most two**, each specific: a topic a reader would follow
  (#CodeReview), not a generic room (#AI, #Programming). `#tags` become
  facets; a tag without a facet is plain text and reaches nobody.
- **LinkedIn: at most five.**

## Links

- **Bluesky: inline, as `[label](url)`.** The label is plain: the page's
  name, or the bare URL. No call-to-action labels. Only the label counts
  toward the 300. `--link` adds a card when the page has one worth showing.
- **X: no URL in the body. The link goes in a reply to the post.** The reply
  carries the URL, written in full with its scheme, and nothing it does not
  need; when there are two, the project home comes first, then the article
  (www#47). The post itself carries no URL and no bare domain X would
  autolink (`codecrew.works`). Cost at the
  [pricing verified 2026-09-26](https://docs.x.com/x-api/getting-started/pricing):
  the plain post is $0.015 and the reply with its URL $0.200, $0.215 against
  $0.200 for one post with the URL inline. The difference buys reach: a post
  with a URL in its body is shown to fewer people. One invocation sends
  both: `post --to x --x-text-file <body>.txt --x-reply-file <links>.txt`
  posts the body, then the file's text as a reply to it, and prints both
  URLs. If the body posts and the reply fails, the tool prints the exact
  `post --to x --reply-to <id> --text-file <links>.txt` to retry the reply
  alone. The commands are in the main README, "Posting to social accounts".
- **LinkedIn: no inline URLs in the post.** The algorithm penalises them
  heavily even though LinkedIn wraps them in its own shortener. The body says
  *"Links in the first comment"*, the post carries no `--link` card, and the
  comment goes up immediately after the post:

  ```sh
  uv run -m social post --to linkedin --linkedin-text-file <body>.txt   # prints the share URN
  uv run -m social comment --urn <that URN> --text-file <links>.txt
  ```

## Approval

- **Low-risk posts need no approval.** A post is low-risk when it only
  announces something already public on GitHub (a release, a milestone
  close, merged work) and says only what the GitHub event and its linked
  record say. It goes out once it passes `social lint`.
- **Everything else the operator approves, the exact text for each
  network, before it goes out:** opinion, comparisons, any claim beyond the
  record (the `why/` pages, "compared", the invite), every reply, and every
  LinkedIn post.
- **Lint failing means no auto-post.** The draft goes to the operator
  instead. An operator-approved text that lint still fails is sent with
  `post --skip-lint`.
- **The record is one comment.** Every post's links go in one comment on the
  milestone issue the post belongs to, when there is one. That comment is
  the only record.

## Before you post

Re-read every draft against the Don't list above, each network's text in
turn, before running lint. Lint checks the mechanical rules below and nothing
else: it cannot tell a fragment opener ("Keyboard fixes on the CodeCrew
site.") from a sentence, nor see a set-up-and-knock-down line, a slogan
antithesis or a rhythmic three. Those are the drafter's to catch, and a post
that passes lint with one of them in it still breaks the guide, as the M24
close post did. A draft you are not sure of goes to the operator.

## The check: `social lint`

```sh
uv run -m social lint --to x --text-file x.txt          # or --to bluesky, --to linkedin; or --text
uv run -m social lint --to x --text-file links.txt --reply   # a reply may carry the link
```

It prints each failure with the rule and the offending fragment and exits 1
on any failure, 0 when the text is clean. `post` runs it on every text
before any network call, dry run included: each network's body (as a reply
when `--reply-to` is given) and the `--x-reply-file` text as a reply. It
refuses a failing text. The rules it checks:

- an em dash anywhere;
- a first sentence ending in a question mark;
- any word or phrase from the list in Don't 8, case-insensitive, as a whole
  word, inflections included;
- a call-to-action label from the list in Don't 5, case-insensitive, with
  either apostrophe, where it opens a phrase: the start of the text or a
  line, after a sentence end, a colon or a semicolon, after an opening quote
  or bracket, or as the start of a Bluesky `[label](url)` label;
- more hashtags than the network allows: X 0, Bluesky 2, LinkedIn 5;
- a URL, or a bare domain X would autolink, in an X post's body (not in a
  reply: the reply is where the link goes);
- emoji;
- "agent-staffed" with a hyphen, or "agent staffed" not followed by ", human
  moderated".

The banned list, the label list and the limits live in `social/lint.py`; a
test pins that this guide and the code agree. The rest of the voice is
judgment (see "Before you post"), and the operator's review of this guide
stands in for reviewing every low-risk post.

## Milestone-close posts

A close post goes out only for a milestone about gh-codecrew itself or how
it is used, per "What CodeCrew posts about": one Bluesky post and one X post
from the CodeCrew accounts, in the voice above. A milestone that only changes
the codecrew.works website gets no post, however small (the operator's
Decision on
[radiusred/gh-codecrew#423](https://github.com/radiusred/gh-codecrew/issues/423#issuecomment-6469436459),
superseding the "every close" clause of the
[earlier one](https://github.com/radiusred/gh-codecrew/issues/423#issuecomment-6467856741),
whose other rules stand: CodeCrew's own accounts, the voice, no per-post
approval when lint passes, links commented on the milestone). A close post
only announces something already public on GitHub, so it is low-risk: it
needs no per-post approval when it passes `social lint`, after the re-read in
"Before you post". The X link goes in the reply, so a close costs $0.215 on
X. One comment with the post links goes on the milestone issue.

## Bluesky budget

300 graphemes, and it is measured, never estimated:

```sh
python3 -c "import sys; sys.path.insert(0,'.'); from social.bluesky import grapheme_len, facets; \
t=open('<draft>.txt').read().strip(); r,_=facets(t); print(grapheme_len(r))"
```

Only the *label* of a `[label](url)` counts toward the limit, so link labels
are short and URLs cost nothing.

## X budget

280 weighted characters, X's rule, not a plain count, measured the same way:

```sh
python3 -c "import sys; sys.path.insert(0,'.'); from social.x import weighted_len; \
print(weighted_len(open('<draft>.txt').read().strip()))"
```

Every URL counts as **23** whatever its length, and a bare domain X would
autolink (`radiusred.uk`, `codecrew.works/blog`) is weighed as a URL too, at
23 or its literal weight, whichever is larger. The guard never under-counts.
Most characters count 1; CJK, emoji and symbols outside the Latin ranges
(`€`, the bullet `•`) count 2; curly quotes count 1. The X text is its own
draft: no URL (it goes in the reply), no `[label](url)` (that is Bluesky
syntax and X would print it verbatim), no `#tags`. `post --to x` refuses an
over-length text before it touches the network, and X would refuse it too,
after billing the try. Costs at the
[pricing verified 2026-09-26](https://docs.x.com/x-api/getting-started/pricing):
$0.015 per post, $0.200 per post containing a URL, credits bought up front.
An announcement is a post plus a link reply, so budget $0.215 per
announcement.

## Credentials

Never in this tree: they live in `~/.config/radiusred/social.env` (see the
main README, "Posting to social accounts"; the old `~/.config/codecrew/`
location is read only until the file is moved). `uv run -m social check`
proves them without posting; `--dry-run` prints the exact request bodies and
touches no network. Neither output is committed anywhere. The X keys and their
pitfall (the 25-character OAuth 1.0 Consumer Key, not the 34-character OAuth
2.0 Client ID) are in the main README; `check` verifies the tokens belong to
the account's handle, and reports an account with no credits as *out of
credits*.
