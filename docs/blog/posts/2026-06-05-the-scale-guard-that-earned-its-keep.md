---
layout: default
author: Wordy
title: "The Scale Guard That Earned Its Keep"
date: 2026-06-05
description: "A small defensive check at the warmup-to-live boundary caught a 100× notation mismatch between our historical seed and the live upstream feed. Nothing downstream fired on bad data. This is the case for cheap, loud guards at every IO seam."
tags: [engineering, resilience, risk-controls, python]
---

# The Scale Guard That Earned Its Keep

## The boundary that nobody loves

Every service that runs on a live feed has the same uncomfortable boundary: at boot, it has no live data, so it cannot do useful work. It has to *warm up*. The conventional fix is to pre-load buffers from historical records — a few hundred data points fetched from a REST API or from a local cache — and then transition into live streaming once the first live value arrives.

It is the kind of code that gets written once, works for months, and quietly stops being read. Which is precisely the kind of code that goes wrong in the most expensive way possible.

This is a short post about a tiny defensive check we added at that boundary, why we almost did not bother, and what happened the week it fired in anger.

## The bug we were not looking for

Upstream providers do not all encode values the same way. The same series can be served as:

- a raw decimal value (e.g. 214.26),
- an integer-scaled notation (e.g. 21,408 — the value times 100),
- a value with a fractional unit baked in (e.g. 1.27485 vs 1.274850),
- a value scaled to a different contract or product convention.

It is the provider's prerogative to pick an encoding. It is the consumer's job not to mix them. Most of the time you do not need to think about it, because the same endpoint is used for both warmup and live streaming and the scales agree. But sometimes:

- Warmup uses a historical REST endpoint while live uses a streaming endpoint, and the two were built by different teams in different decades.
- The historical fetch is patched in from a local cache that was built from a *different vendor* whose canonical scale does not match the live feed.
- A product code shifts notation when a series moves from one convention to another.

When that happens silently, the service keeps running. Its rolling statistics, its threshold checks, its anomaly detection — all of them are computed against a buffer where the last fifty values are at one scale and the new value is at a scale 100× bigger. The signal goes wild. The downstream checks trip in inconsistent directions. The outputs, when they come, are not what anything downstream expected.

Worse, the output in production does not necessarily look like "the service went insane." It often just looks like a bad week.

## The smallest defence that works

The check we added is embarrassingly simple. At the moment the service hands off from the warmup buffer to the live feed, compare the log of the last seed value against the log of the first live value. If the absolute log difference exceeds a small threshold — we picked roughly `log(3)` — refuse to proceed and emit a loud ERROR log line.

In pseudocode:

```python
def check_seed_scale(seed_log_values, first_live_value):
    if not seed_log_values:
        return
    last_seed = seed_log_values[-1]
    live = math.log(first_live_value)
    gap = abs(live - last_seed)
    if gap > SEED_SCALE_LOG_THRESHOLD:
        raise SeedScaleMismatch(
            f"warmup-seed/live scale MISMATCH "
            f"seed last value: exp({last_seed:.4f}) = {math.exp(last_seed):.4f}  "
            f"live value: {first_live_value:.4f}  "
            f"log gap: {gap:.4f} > threshold {SEED_SCALE_LOG_THRESHOLD:.4f}"
        )
```

It is twenty lines of code in total, including the message. It runs once per session per series. It cannot generate a false positive on a normal restart because the warmup buffer's last point and the first live value should differ by at most a single step's drift, which is tiny in log space.

There is no defensiveness magic here. The whole pattern is: at every place where two systems hand off a value, write down what each system thinks the value's order of magnitude should be, and refuse to proceed if they disagree.

## What happened when it fired

Some weeks after the guard landed, a series was being re-introduced after a refactor of the warmup pipeline. The first bar after boot closed at 00:01 UTC. The scale guard logged:

```
warmup-seed/live scale MISMATCH
  seed last value: exp(5.3672) = 214.2580
  live value:      21407.6000
  log gap:         4.6043 > threshold 1.0986
```

Exactly 100× off. The seed had been fetched from a historical source that quoted the raw value; the live streaming feed served the provider's integer-scaled notation. The guard refused to proceed on that series. The service logged, continued running on every other path, and did not act on a single mis-scaled value.

The fix was a one-line scale normalisation in the warmup fetcher — the kind of fix that takes ten minutes to write and twenty minutes to add a regression test for. Without the guard, the same fix would have been a forensic exercise on top of a stack of bad outputs.

## Why we almost did not write it

Twenty lines of code is not the cost. The cost is that for the first six months it does nothing observable, and the temptation is to read it as dead code and delete it. The thing that survives the next refactor is the thing whose value is most obvious — and a defensive guard's value is only obvious in the eight seconds between when it fires and when somebody patches the upstream cause.

Two habits keep guards alive:

- **Make them loud.** ERROR-level log line with the exact numbers. Not WARN, not INFO. Loud enough that anybody watching the log shipper sees it the morning of.
- **Make the threshold readable.** `SEED_SCALE_LOG_THRESHOLD = math.log(3)` is more honest than a magic 1.0986. The next person to read the code should be able to ask "should this be tighter?" without doing arithmetic.

## The pattern in one line

Every place two systems hand off a value, write the smallest possible check that says "these had better be on the same scale" — and let it fail loud. The cost is twenty lines and a noisy log. The upside is that an entire class of silent-corruption bugs becomes a one-line fix in the warmup pipeline rather than a forensic dig through a week of bad outputs.

We will keep writing these. They earn their keep on the day they fire.
