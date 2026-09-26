# Announcement guidelines

Standing rules for anything posted from the Radius Red accounts through the
`social` package. They come from the operator's reviews on
[www#47](https://github.com/radiusred/www/issues/47) and
[PR #54](https://github.com/radiusred/www/pull/54) and apply to every
announcement until they are changed here.

Each announcement gets a dated file in this directory — the texts, the
research behind the tags, the exact commands, the captured `--dry-run`, and a
Result section that takes the post URLs after they go out. The posting itself
is a gated act: a `cc:needs-decision` checkpoint on the task issue, resolved by
the operator, and the PR merges after the URLs are in the file.

The gate is per announcement and per network, and X is no exception: an X
post goes out only when its checkpoint names it, run by hand with
`post --to x`, one announcement at a time. There is no automated
cross-posting — nothing posts to X because something was posted elsewhere —
and no backfill: announcements that went out before the X account existed
stay where they are (M7-R7 on
[radiusred/ops#28](https://github.com/radiusred/ops/issues/28)). Every X post
costs money (see the X budget below), which is one more reason the gate is
per post.

## Write for someone who has never heard of us

Plain speech, until the project is a household name. Simple, hard-hitting,
factual. No insider vocabulary: not "cycles", not "protocol gates", not "seats"
or "the coordination layer" — a reader who knows neither our product nor the
platform we are talking about should still understand what happened and why it
mattered. Name the other products involved; do not allude to them. Anyone who
wants the detail follows the link and reads the article, which is where the
vocabulary belongs.

Claims stay factual and traceable to the record. Plain does not mean loose.

## Links

- **Project home first, the article second.** Standing instruction from
  www#47. On Bluesky both are inline links; on LinkedIn both are in the first
  comment.
- **No inline URLs in a LinkedIn post.** The algorithm penalises them heavily
  even though LinkedIn wraps them in its own shortener. The body says *"Links
  in the first comment"*, and the comment goes up immediately after the post:

  ```sh
  uv run -m social post --to linkedin --linkedin-text-file <body>.txt   # prints the share URN
  uv run -m social comment --urn <that URN> --text-file <links>.txt
  ```

  For the same reason the LinkedIn post carries **no `--link` card** — pass
  `--link` only on the Bluesky invocation, which means the two networks are two
  commands rather than one.
- **X: links inline in the body.** The standing rule, recorded as the
  operator's Decision on the milestone
  ([radiusred/ops#28, 2026-09-26](https://github.com/radiusred/ops/issues/28#issuecomment-5846341962)),
  is LinkedIn's: URLs go in a reply *only if that reply is free*. At the
  [pricing verified that day](https://docs.x.com/x-api/getting-started/pricing)
  a post containing a URL costs $0.200 and a reply containing one costs the
  same, so a link reply buys nothing: **the URLs go in the body**, one post,
  $0.200, instead of a plain post plus a reply at $0.215. The transport has
  no reply path and takes no `--link` card. Project home first, the article
  second, as everywhere; write the URLs in full with their scheme (each counts
  as 23). Once the account has credits, the first billed post is checked
  against the console's usage; if X ever bills a URL reply below a URL post,
  the Decision is revisited on the milestone, not silently reversed.

## Bluesky budget

300 graphemes, and it is measured, never estimated:

```sh
python3 -c "import sys; sys.path.insert(0,'.'); from social.bluesky import grapheme_len, facets; \
t=open('announcements/<file>.txt').read().strip(); r,_=facets(t); print(grapheme_len(r))"
```

Only the *label* of a `[label](url)` counts toward the limit, so link labels
are short and URLs cost nothing. `#tags` become facets; a tag without a facet
is plain text and reaches nobody.

## X budget

280 weighted characters — X's rule, not a plain count — measured the same way:

```sh
python3 -c "import sys; sys.path.insert(0,'.'); from social.x import weighted_len; \
print(weighted_len(open('announcements/<file>.txt').read().strip()))"
```

Every URL counts as **23** whatever its length. Most characters count 1;
CJK, emoji (a whole sequence, skin tone and all, is one emoji at 2) and
symbols outside the Latin ranges — `€`, the bullet `•` — count 2; the em dash
and curly quotes count 1. The X text is its own file (`x-<date>.txt`): plain
URLs, no `[label](url)` (that is Bluesky syntax and X would print it
verbatim), `#tags` as plain text. `post --to x` refuses an over-length text
before it touches the network, and X would refuse it too — after billing the
try. Costs at the [pricing verified 2026-09-26](https://docs.x.com/x-api/getting-started/pricing):
$0.015 per post, $0.200 per post containing a URL, credits bought up front;
an announcement carries links, so budget $0.200 per announcement.

## Tags are measured, not guessed

The operator asks for research rather than instinct.

- **Bluesky:** volume through the authenticated `app.bsky.feed.searchPosts`
  (the public appview refuses an unauthenticated caller), reported as *hours
  for a tag to accumulate its latest 100 posts* — smaller is busier. Keep the
  metric identical between announcements so the runs are comparable, and
  re-measure each time; the table goes in the announcement file. Measure the
  obvious tags too: the ones instinct reaches for are often empty rooms.
- **LinkedIn:** 3–5 tags. Follower counts are no longer exposed in the feed,
  so cite published guide figures and the tier they imply — at most one Tier-1
  (1M+) anchor, Tier-2 (100K–1M) as the workhorses, Tier-3 (10K–100K) where
  engagement is highest. A tag with no published figure is chosen on relevance
  and *said to be*, not dressed up as a measurement.
- **X: unmeasured, for now.** The Bluesky method needs a search endpoint, and
  on X's pay-per-use project `GET /2/tweets/search/recent` is billed per post
  returned ($0.005 each at the pricing verified 2026-09-26; a 100-post sample
  per candidate tag is $0.50, twenty candidates $10) — and the account has no
  credits, so no measurement was possible when the transport was added
  (M7-R4, [radiusred/ops#28](https://github.com/radiusred/ops/issues/28)).
  Until it is measured, X tags are chosen on relevance, leaning on the
  Bluesky table for the same announcement, and the announcement file says so
  plainly, as the LinkedIn rule does. Revisit once credits exist: the method
  would be the Bluesky one (hours for a tag to accumulate its latest 100
  posts, `sort_order=recency`, `max_results=100`), costed per run before it is
  run.

## Credentials

Never in this tree: they live in `~/.config/radiusred/social.env` (see the
main README, "Posting to social accounts"; the old `~/.config/codecrew/`
location is read only until the file is moved). `uv run -m social check`
proves them without posting; `--dry-run` prints the exact request bodies and
touches no network. Both outputs are captured into the announcement file, and
scanned for tokens before they are committed. The X keys and their pitfall
(the 25-character OAuth 1.0 Consumer Key, not the 34-character OAuth 2.0
Client ID) are in the main README; `check` verifies the tokens belong to
`@radiusred_uk`, and reports an account with no credits as *out of credits*.
