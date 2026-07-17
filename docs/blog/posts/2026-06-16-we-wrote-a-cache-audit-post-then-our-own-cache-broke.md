---
layout: default
author: Wordy
title: "We Wrote a Cache Audit Post. Then Our Own Cache Broke."
date: 2026-06-16
description: "Two weeks ago we published a post about auditing a data cache. This week, our own audit caught us. The default value we shipped as 'optional' was silently producing 100× wrong scales; the safety check that was supposed to refuse them was doing exactly that — and the routine around it cheerfully reported 'success' anyway. Here is what happened, what we changed, and the general lesson for anyone running a cache-driven pipeline."
tags: [engineering, data-quality, open-source, postmortem]
---

# We Wrote a Cache Audit Post. Then Our Own Cache Broke.

## The embarrassing part

Two weeks ago we published [a post on auditing a data cache before you trust what's downstream](/blog/posts/2026-06-09-auditing-a-market-data-cache-before-you-trust-a-backtest). The argument was simple: a downstream result is only as honest as the data it touches, and the cheapest defence is to run mechanical checks at the cache level before any result is allowed to matter.

This week, our own audit caught us.

The bugs are funny. They are also exactly the kind of bug the audit post was written to surface. The most embarrassing part is not that we had them — every research codebase eventually does — it is that the bugs had been there for months, that the safety checks we had built *were working*, and that the routine around them reported "success" anyway.

This post walks through both bugs, what we changed, and the general lesson we are taking away. All of it is in one of our open-source data tools' daily refresh routine. No private research output, internal parameters, or production deployment details are referenced in this article.

## Bug #1 — The daily refresh that did not refresh

The first symptom was the easiest to miss, because the routine that exhibited it reported "success" every time it ran.

The daily refresh is a small wrapper around our public export CLI. It walks the list of configured series, calls the export command for each one with the right identifier and date range, and then exits with `0` if every per-series export returned. The intent is that the cache is at most one day behind at the end of the run.

The CLI takes a `--scale-divisor` argument that controls how the raw source value is normalised. Different series quote at different scales — raw value, integer points, fractional units — and the divisor is how the tool reconciles them onto a single canonical column. The argument was marked optional in the CLI; the default is `1.0`.

That default is the bug.

What happened in production: a config change earlier in the year added a handful of series whose canonical scale was *not* 1.0. For those series, every daily call passed `--scale-divisor 1.0` implicitly, and the export wrote a candle whose median was the raw value expressed at a different scale than the rest of the cache. For most of our series the default happened to be right, so most refreshed normally. For the handful that needed a non-1.0 divisor, the export wrote a single day, and then a separate safety check caught the inconsistency and refused the write.

The safety check is the part of this story we are still arguing about over lunch.

The check is a scale-sentry: the same idea used elsewhere in our tooling to catch a scale break at a warmup-to-live boundary, generalised here to the daily refresh. It computes the median of the new day's candles and compares it against the median of the last few days already on disk. If the absolute log difference exceeds a small threshold — `log(3)` — it refuses the write, logs a loud ERROR, and returns non-zero.

The scale-sentry did exactly what it was supposed to do. It refused the writes. The wrong-scale days never made it to disk. The cache stayed on yesterday's data for those series.

The problem is one level up. The daily refresh treats a per-series failure as a *soft* failure. It logs the failure, decrements a per-series counter, and continues. At the end of the loop, it checks the exit code of the *loop driver*, not the per-series results. The loop driver exited 0. The routine as a whole reported "success" because nothing it was looking at had failed.

The signal we should have built in is obvious in hindsight: "daily refresh wrote N series where N == expected" is a different statement from "daily refresh exited 0". We had been checking the second. The first is the one that mattered.

By the time we noticed, the cache was a day behind on those series, and we had no record of any single day having been wrong, only that the writes had been refused. The scale-sentry ERROR logs were sitting in the journal the whole time, but the error was logged and not escalated by the routine boundary — the routine's exit code was 0, and nothing in the loop's contract required it to be anything else.

## Bug #2 — The historical cache that had been wrong for months

The audit that surfaced bug #1 also surfaced bug #2, and bug #2 is the worse one.

The scale-sentry was checking the new day against the *last few days on disk*. The new day was wrong; the last few days on disk were also wrong, in the same direction, because the cache had been wrong for the entire history of those series.

Concretely, the pattern looked like this:

- One series' canonical scale was supposed to be roughly 1.16. The cache had it at 116.
- A second series' canonical scale was supposed to be roughly 158.9. The cache had it at 1.589.
- A third was off by 10×.

None of the per-series internal metrics had ever complained. Autocorrelation is scale-invariant. Rolling volatility is scale-invariant. Band width is scale-invariant. The only check that was ever going to catch this was an end-to-end check against an external reference — which, conveniently, is the audit post we had just published.

The fix was a one-off whole-cache rescale: walk every candle file, look up the canonical scale for the series, and divide through. What we kept, what we threw out, and what we re-fetched is not interesting in detail; the shape of the operation is what matters. The rescale was logged as a one-off provenance event in the cache metadata so we can reconstruct, from a single cache directory, exactly which series were touched and when.

The single sharpest feeling in the whole exercise was the moment we realised that the audit post — the one we had just shipped — was the thing that found this. The cross-provider check described in that post is a couple of hundred lines of script. We had been sitting on the bug for months because the discipline of running that script against the cache was not yet part of the standard workflow. It is now.

## What we changed

Two changes, both in the open-source repo:

1. **Per-series `--scale-divisor` is now passed explicitly by the routine.** The CLI still accepts the default of `1.0` for ad-hoc use, but the daily refresh fetcher passes the divisor from a per-series config table on every call. The config table is the single source of truth. There is no path through the routine in which the default is used for a configured series.
2. **The routine now asserts "N expected series advanced today" before exiting 0.** A successful exit means: every configured series has a new day on disk, the count of new days equals the count of configured series, and the scale-sentry log contains zero ERROR lines from this run. If any of those checks fail, the routine exits non-zero and a single top-level error message names which check failed.

A third change, internal to our own operations rather than the open-source repo, is that the alerting and escalation around daily-refresh failures was tightened. The routine's own exit assertion is now the contract we trust, and a soft-failure of this shape can no longer go unreported for weeks.

## The general lesson

There are two general lessons, and they are different in kind.

The first is that a routine that does not fail is not the same as a routine that succeeds. The scale-sentry did not fail. The daily refresh did not fail. The loop driver did not fail. The whole system failed in the most boring way possible, by having every individual component behave correctly and the overall result still be wrong. The fix is not to make any of those components noisier. The fix is to have one component whose job is to check the *result* — the count of new days, the count of expected series, the count of refused writes — and refuse to call the routine a success on the basis of exit codes alone.

The second is that default arguments in CLI plumbing are a category of silent risk distinct from logic bugs. A logic bug will eventually fail a test, or produce an obviously wrong output, or get caught by code review. A default argument that is wrong for one subset of inputs is a logic bug that only fails for that subset, and the failure mode is "the output looks fine, it is just at a different scale than the rest of your data." There is no exception, no traceback, no test failure. The discipline is the same as for any other silent failure: have a check that *expects* the output to be in a known range, and refuse to proceed if it is not.

The third thing we are taking away, and it is the one that is most uncomfortable to write down, is that we had the audit pipeline that would have caught this for over a month, and we had not yet wired it into the standard workflow. The cost of writing the audit was small. The cost of *not running* the audit was three months of bad cache data, a one-off whole-cache rescale, and this post.

## What the audit post was for

If you maintain a data cache and you do not run an end-to-end audit at the cache level — please go and write one this afternoon. The bug you will find will not be the one you expected.

The post we wrote two weeks ago was about exactly this discipline. It is now also the post we wrote about ourselves.
