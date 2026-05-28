---
layout: default
author: Wordy
title: "The Scale Guard That Earned Its Keep"
date: 2026-06-05
description: "A small defensive check at the warmup-to-live boundary caught a 100× notation mismatch between our historical seed and the live broker feed. No trades fired. This is the case for cheap, loud guards at every IO seam."
tags: [engineering, systematic-trading, risk-controls, python]
---

# The Scale Guard That Earned Its Keep

## The boundary that nobody loves

Every systematic strategy that runs on a live feed has the same uncomfortable boundary: at boot, it has no live data, so it cannot trade. It has to *warm up*. The conventional fix is to pre-load the strategy's indicator buffers from historical bars — a few hundred candles fetched from the broker REST API or from a local cache — and then transition into live streaming once the first live tick arrives.

It is the kind of code that gets written once, works for months, and quietly stops being read. Which is precisely the kind of code that goes wrong in the most expensive way possible.

This is a short post about a tiny defensive check we added at that boundary, why we almost did not bother, and what happened the week it fired in anger.

## The bug we were not looking for

Brokers do not all quote prices the same way. The same instrument can be served as:

- a raw exchange rate (e.g. GBP/JPY ≈ 214.26),
- an integer point notation (e.g. 21,408 — the rate times 100),
- a price with a fractional pip baked in (e.g. 1.27485 vs 1.274850),
- a tick scaled to a contract's tick size.

It is the broker's prerogative to pick a notation. It is the strategy's job not to mix them. Most of the time you do not need to think about it, because the same endpoint is used for both warmup and live streaming and the scales agree. But sometimes:

- Warmup uses a historical REST endpoint while live uses a streaming endpoint, and the two were built by different teams in different decades.
- The historical fetch is patched in from a local cache that was built from a *different vendor* whose canonical scale does not match the live broker.
- A product code shifts notation when an instrument moves from spot to "today's expiry" or to a different contract series.

When that happens silently, the strategy keeps trading. Its rolling z-score, its Bollinger band, its breakout threshold — all of them are computed against a buffer where the last fifty values are at one scale and the new value is at a scale 100× bigger. The signal goes wild. The risk filters trip in inconsistent directions. The fills, when they come, are not the trades the strategy thought it was placing.

Worse, the equity curve in production does not necessarily look like "the strategy went insane." It often just looks like a bad week.

## The smallest defence that works

The check we added is embarrassingly simple. At the moment the strategy hands off from the warmup buffer to the live feed, compare the log of the last seed close against the log of the first live close. If the absolute log difference exceeds a small threshold — we picked roughly `log(3)` — refuse to trade and emit a loud ERROR log line.

In pseudocode:

```python
def check_seed_scale(seed_log_closes, first_live_close):
    if not seed_log_closes:
        return
    last_seed = seed_log_closes[-1]
    live = math.log(first_live_close)
    gap = abs(live - last_seed)
    if gap > SEED_SCALE_LOG_THRESHOLD:
        raise SeedScaleMismatch(
            f"warmup-seed/live price-scale MISMATCH "
            f"seed last close: exp({last_seed:.4f}) = {math.exp(last_seed):.4f}  "
            f"live close: {first_live_close:.4f}  "
            f"log gap: {gap:.4f} > threshold {SEED_SCALE_LOG_THRESHOLD:.4f}"
        )
```

It is twenty lines of code in total, including the message. It runs once per session per instrument. It cannot generate a false positive on a normal restart because the warmup buffer's last bar and the first live tick should differ by at most a single bar's drift, which is tiny in log space.

There is no defensiveness magic here. The whole pattern is: at every place where two systems hand off a value, write down what each system thinks the value's order of magnitude should be, and refuse to proceed if they disagree.

## What happened when it fired

Some weeks after the guard landed, an instrument was being re-introduced after a refactor of the warmup pipeline. The first DAY bar after boot closed at 00:01 UTC. The scale guard logged:

```
warmup-seed/live price-scale MISMATCH
  seed last close: exp(5.3672) = 214.2580
  live close:      21407.6000
  log gap:         4.6043 > threshold 1.0986
```

Exactly 100× off. The seed had been fetched from a historical source that quoted the raw rate; the live streaming feed served the broker's integer point notation. The guard refused entries on that instrument. The strategy logged, continued running on every other sleeve, and did not fire a single trade against the mis-scaled data.

The fix was a one-line scale normalisation in the warmup fetcher — the kind of fix that takes ten minutes to write and twenty minutes to add a regression test for. Without the guard, the same fix would have been a forensic exercise on top of a stack of bad trades.

## Why we almost did not write it

Twenty lines of code is not the cost. The cost is that for the first six months it does nothing observable, and the temptation is to read it as dead code and delete it. The thing that survives the next refactor is the thing whose value is most obvious — and a defensive guard's value is only obvious in the eight seconds between when it fires and when somebody patches the upstream cause.

Two habits keep guards alive:

- **Make them loud.** ERROR-level log line with the exact numbers. Not WARN, not INFO. Loud enough that anybody watching the log shipper sees it the morning of.
- **Make the threshold readable.** `SEED_SCALE_LOG_THRESHOLD = math.log(3)` is more honest than a magic 1.0986. The next person to read the code should be able to ask "should this be tighter?" without doing arithmetic.

## The pattern in one line

Every place two systems hand off a value, write the smallest possible check that says "these had better be on the same scale" — and let it fail loud. The cost is twenty lines and a noisy log. The upside is that an entire class of silent-corruption bugs becomes a one-line fix in the warmup pipeline rather than a forensic dig through a week of bad trades.

We will keep writing these. They earn their keep on the day they fire.
