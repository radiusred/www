---
layout: default
author: Wordy
title: "We Wrote a Cache Audit Post. Then Our Own Cache Broke."
date: 2026-06-16
description: "Two weeks ago we published a post about auditing a market-data cache. This week, our own audit caught us. The default value we shipped as 'optional' was silently producing 100× wrong price scales; the safety check that was supposed to refuse them was doing exactly that — and the routine around it cheerfully reported 'success' anyway. Here is what happened, what we changed, and the general lesson for anyone running a cache-driven backtest."
tags: [engineering, data-quality, backtesting, open-source, postmortem]
---

# We Wrote a Cache Audit Post. Then Our Own Cache Broke.

## The embarrassing part

Two weeks ago we published [a post on auditing a market-data cache before you trust a backtest](/blog/posts/2026-06-09-auditing-a-market-data-cache-before-you-trust-a-backtest). The argument was simple: a backtest is only as honest as the data it touches, and the cheapest defence is to run mechanical checks at the cache level before any result is allowed to matter.

This week, our own audit caught us.

The bugs are funny. They are also exactly the kind of bug the audit post was written to surface. The most embarrassing part is not that we had them — every research codebase eventually does — it is that the bugs had been there for months, that the safety checks we had built *were working*, and that the routine around them reported "success" anyway.

This post walks through both bugs, what we changed, and the general lesson we are taking away. All of it is in the open-source [`tradedesk-dukascopy`](https://github.com/radiusred/tradedesk-dukascopy) daily refresh routine. No live strategy IP is touched; nothing in this post references backtest results, specific instrument decisions, or internal strategy names.

## Bug #1 — The daily refresh that did not refresh

The first symptom was the easiest to miss, because the routine that exhibited it reported "success" every time it ran.

The Dukascopy daily refresh in `tradedesk-dukascopy` is a small wrapper around the public `tradedesk-dc-export` CLI. It walks the list of configured symbols, calls `tradedesk-dc-export export` for each one with the right symbol and date range, and then exits with `0` if every per-symbol export returned. The intent is that the cache is at most one day behind at the end of the run.

The CLI takes a `--price-divisor` argument that controls how the raw Dukascopy tick price is normalised. Different instruments quote at different scales — raw exchange rate, integer points, fractional pip — and the divisor is how the tool reconciles them onto a single canonical price column. The argument was marked optional in the CLI; the default is `1.0`.

That default is the bug.

What happened in production: a config change earlier in the year added a handful of instruments whose canonical scale was *not* 1.0. For those symbols, every daily call passed `--price-divisor 1.0` implicitly, and the export wrote a candle whose median was the raw exchange rate expressed at a different scale than the rest of the cache. For most of our instruments the default happened to be right, so 15 of 33 symbols refreshed normally. For the 18 that needed a non-1.0 divisor, the export wrote a single day, and then a separate safety check caught the inconsistency and refused the write.

The safety check is the part of this story we are still arguing about over lunch.

The check is `scale_sentry` (the same idea from [RAD-1920](https://github.com/radiusred/tradedesk-dukascopy) that catches a price-scale break at the warmup-to-live boundary, but generalised to the daily refresh). It computes the median of the new day's candles and compares it against the median of the last few days already on disk. If the absolute log difference exceeds a small threshold — `log(3)` — it refuses the write, logs a loud ERROR, and returns non-zero.

`scale_sentry` did exactly what it was supposed to do. It refused the writes. The 18 wrong-scale days never made it to disk. The cache stayed on yesterday's data for those 18 instruments.

The problem is one level up. The daily refresh treats a per-symbol failure as a *soft* failure. It logs the failure, decrements a per-symbol counter, and continues. At the end of the loop, it checks the exit code of the *loop driver*, not the per-symbol results. The loop driver exited 0. The routine as a whole reported "success" because nothing it was looking at had failed.

The signal we should have built in is obvious in hindsight: "daily refresh wrote N symbols where N == expected" is a different statement from "daily refresh exited 0". We had been checking the second. The first is the one that mattered.

By the time we noticed, the cache was 1 day behind on those 18 symbols, and we had no record of any single day having been wrong, only that the writes had been refused. The `scale_sentry` ERROR logs were sitting in the journal the whole time, but the error was logged and not escalated by the routine boundary — the routine's exit code was 0, and nothing in the loop's contract required it to be anything else.

## Bug #2 — The historical cache that had been wrong for months

The audit that surfaced bug #1 also surfaced bug #2, and bug #2 is the worse one.

`scale_sentry` was checking the new day against the *last few days on disk*. The new day was wrong; the last few days on disk were also wrong, in the same direction, because the cache had been wrong for the entire history of those symbols.

Concretely, the pattern looked like this:

- One of the symbols was a major FX pair whose canonical scale was supposed to be 1.16-ish. The cache had it at 116.
- A second symbol was a JPY-cross whose canonical scale was supposed to be 158.9. The cache had it at 1.589.
- A third was a CAD-cross off by 10×.

None of the per-instrument internal metrics had ever complained. Autocorrelation is scale-invariant. Rolling vol is scale-invariant. Bollinger band width is scale-invariant. The only check that was ever going to catch this was an end-to-end check against an external reference — which, conveniently, is the audit post we had just published.

The fix was a one-off whole-cache rescale: walk every candle file, look up the canonical scale for the symbol, and divide through. What we kept, what we threw out, and what we re-fetched is not interesting in detail; the shape of the operation is what matters. The rescale was logged as a one-off provenance event in the cache metadata so we can reconstruct, from a single cache directory, exactly which symbols were touched and when.

The single sharpest feeling in the whole exercise was the moment we realised that the audit post — the one we had just shipped — was the thing that found this. The cross-provider check described in that post is a 200-line script. We had been sitting on the bug for months because the discipline of running that script against the cache was not yet part of the standard workflow. It is now.

## What we changed

Two changes, both of them in the open-source repo:

1. **Per-symbol `--price-divisor` is now passed explicitly by the routine.** The CLI still accepts the default of `1.0` for ad-hoc use, but the daily refresh fetcher passes the divisor from a per-symbol config table on every call. The config table is the single source of truth. There is no path through the routine in which the default is used for a configured symbol. (See the routine update referenced as [RAD-2684](https://github.com/radiusred/tradedesk-dukascopy) in the changelog.)
2. **The routine now asserts "N expected symbols advanced today" before exiting 0.** A successful exit means: every configured symbol has a new day on disk, the count of new days equals the count of configured symbols, and the `scale_sentry` log contains zero ERROR lines from this run. If any of those checks fail, the routine exits non-zero and a single top-level error message names which check failed.

A third change, internal to our own operations rather than the open-source repo, is that the alerting and escalation around daily-refresh failures was tightened. The routine's own exit assertion is now the contract we trust, and a soft-failure of this shape can no longer go unreported for weeks.

## The general lesson

There are two general lessons, and they are different in kind.

The first is that a routine that does not fail is not the same as a routine that succeeds. `scale_sentry` did not fail. The daily refresh did not fail. The loop driver did not fail. The whole system failed in the most boring way possible, by having every individual component behave correctly and the overall result still be wrong. The fix is not to make any of those components noisier. The fix is to have one component whose job is to check the *result* — the count of new days, the count of expected symbols, the count of refused writes — and refuse to call the routine a success on the basis of exit codes alone.

The second is that default arguments in CLI plumbing are a category of silent risk distinct from logic bugs. A logic bug will eventually fail a test, or produce an obviously wrong output, or get caught by code review. A default argument that is wrong for one subset of inputs is a logic bug that only fails for that subset, and the failure mode is "the output looks fine, it is just at a different scale than the rest of your data." There is no exception, no traceback, no test failure. The discipline is the same as for any other silent failure: have a check that *expects* the output to be in a known range, and refuse to proceed if it is not.

The third thing we are taking away, and it is the one that is most uncomfortable to write down, is that we had the audit pipeline that would have caught this for over a month, and we had not yet wired it into the standard workflow. The cost of writing the audit was small. The cost of *not running* the audit was three months of bad cache data, a one-off whole-cache rescale, and this post.

## What the audit post was for

If you maintain a market-data cache and you do not run an end-to-end audit at the cache level — please go and write one this afternoon. The bug you will find will not be the one you expected.

The post we wrote two weeks ago was about exactly this discipline. It is now also the post we wrote about ourselves.

---

**Sources and code**: All audit code is in the public [`tradedesk-dukascopy`](https://github.com/radiusred/tradedesk-dukascopy) repository under `scripts/dukascopy_audit.py` and `scripts/dukascopy_cross_provider.py`. The daily refresh routine, the `scale_sentry` safety check, and the per-symbol `--price-divisor` config table are all in the same repo. No private research output, strategy parameters, or live deployment details are referenced in this article.
