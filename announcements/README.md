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

## Bluesky budget

300 graphemes, and it is measured, never estimated:

```sh
python3 -c "import sys; sys.path.insert(0,'.'); from social.bluesky import grapheme_len, facets; \
t=open('announcements/<file>.txt').read().strip(); r,_=facets(t); print(grapheme_len(r))"
```

Only the *label* of a `[label](url)` counts toward the limit, so link labels
are short and URLs cost nothing. `#tags` become facets; a tag without a facet
is plain text and reaches nobody.

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

## Credentials

Never in this tree. `uv run -m social check` proves them without posting;
`--dry-run` prints the exact request bodies and touches no network. Both
outputs are captured into the announcement file, and scanned for tokens before
they are committed.
