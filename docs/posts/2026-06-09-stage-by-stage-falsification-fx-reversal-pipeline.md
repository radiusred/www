---
title: "Stage-by-Stage Falsification: Inside Our FX Reversal Research Pipeline"
date: 2026-06-09
description: "Most strategy ideas die before they ever touch live capital. This is a walk-through of the multi-stage falsification pipeline we use to decide whether a published anomaly — in this case, short-term FX reversal on G10 USD pairs — earns the right to be tested for deployment."
tags: [research, systematic-trading, methodology]
---

# Stage-by-Stage Falsification: Inside Our FX Reversal Research Pipeline

## Introduction

Most strategy ideas die before they ever touch live capital. The interesting question is not *which one wins* — it is *how a strategy earns the right to be tested seriously*.

This article walks through the multi-stage falsification pipeline we use to decide that. We use a current example: short-term cross-sectional reversal on G10 USD foreign exchange pairs. The hypothesis comes from a well-known academic anchor; what is interesting is the process by which we either let it survive or kill it.

Two things this article is *not*: it is not a backtest report — the Stage-1 results for this hypothesis are still under internal review and not for publication. And it is not advice. It is a methodology piece for sophisticated retail traders and institutional researchers who care about how a small team decides what is worth trading and what to walk away from.

## The Pipeline in One Diagram

Every candidate strategy moves through three falsification stages before it can be considered for live deployment:

| Stage | Question it answers | Output |
|---|---|---|
| **Stage-0 — Anchor sweep** | Is there a directional signal at all in our cost regime and data window? | A small grid of cells with out-of-sample summary metrics; a go/no-go on whether to invest more time. |
| **Stage-1 — Falsification harness** | Does the signal survive an honest in-sample/out-of-sample split, walk-forward retests, and a cost-fuzz sensitivity sweep? | A pass / borderline / fail verdict against pre-registered gates. |
| **Stage-2 — Live-paper sizing** | Does the signal survive real broker microstructure, slippage and execution behaviour at our target position size? | A live-paper P&L curve and operational notes that feed the portfolio-fit decision. |

The pipeline is deliberately conservative. Anything that passes Stage-0 still has two more stages where it can be falsified. Anything that passes Stage-1 is still not promoted to live capital — only to live-paper.

We treat the gates as one-way doors. Failure at any stage is a kill, not a "try harder". A strategy can come back later with a genuinely different formulation, but the prior attempt is filed and counts.

## The Hypothesis: Short-Term FX Reversal

The current Stage-1 candidate is a textbook short-term reversal:

- **Universe**: G10 USD currency pairs — EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF, NZDUSD.
- **Signal**: rank each pair by its trailing W-week total return.
- **Trade rule**: long the worst performers (bottom k), short the best performers (top k), equal-weighted and dollar-neutral.
- **Holding period**: monthly rebalance, daily bars.

The academic lineage is well established. Lehmann (1990, *Fads, Martingales, and Market Efficiency*) is the canonical short-term reversal reference. More recently, the cross-sectional FX literature has explored how momentum and reversal interact at different time horizons (Menkhoff et al. 2012; Asness, Moskowitz & Pedersen 2013). Our anchor read combined a slow momentum leg with a faster reversal leg in cross-sectional FX — but the result of Stage-0 made us drop half of the idea.

## Stage-0: The Anchor Sweep

Stage-0 is intentionally cheap. The point is to find out whether there is any sign of life in the signal *in our specific cost regime, on our specific data, in our specific out-of-sample window* — before we sink real engineering time into a fuller harness.

For this hypothesis, the Stage-0 sweep tested a small grid of the dual-speed combined strategy:

- Several reversal lookback windows (W in weeks).
- Several momentum lookback windows (M in months).
- Two cross-sectional quantile choices (tercile, quintile).
- A blend parameter mixing the reversal leg and the momentum leg.

Data was Dukascopy daily mid-prices for the G10 USD pairs, with a fixed out-of-sample window. Costs were per-pair median spreads sampled from the same cache, scaled to be deliberately punitive.

The qualitative result was the interesting one. Across every parameter combination we tested:

- The **reversal-only** sub-strategy outperformed the **momentum-only** sub-strategy on the same data and the same window — every single cell.
- The **combined dual-speed** strategy underperformed the **reversal-only** version once cost-aware metrics were used.
- Parameter-fuzz on the blend coefficient kept collapsing toward "essentially all reversal".

You can read that as the data telling us, fairly bluntly, that the *momentum half of the anchor paper does not exist in this universe and this window*. Combining a non-existent momentum signal with a real reversal signal does not help; it just dilutes the part that worked.

So the decomposition decision was easy: drop the momentum leg, isolate the reversal leg, and promote *that* to Stage-1.

We deliberately do not publish the Stage-0 numbers themselves. The point of Stage-0 is decision support, not a publishable claim. What we will publish are results that have survived Stage-1's stricter design.

## Stage-1: The Falsification Harness

Stage-1 is where the strategy meets a much less forgiving evaluation framework. The harness is designed to break the strategy if it can be broken at low cost, before any capital decision is taken.

The Stage-1 design for FX reversal has four pillars.

### 1. A Wider Parameter Grid

Stage-1 widens the reversal lookback to W ∈ {1, 2, 3, 4} weeks and the cross-sectional cut to {tercile, quintile, decile}. That is 12 base cells, reported individually. "Best cell" is *not* allowed to be the headline; the cross-W and cross-quantile tables are.

This matters because the most common way a backtest lies to you is by collapsing a parameter surface to its best point. The right defence is to publish the surface, not the peak.

### 2. An Honest IS/OOS Split

The full window is split into a definite in-sample period and a definite out-of-sample period. Parameter selection, if any, happens on in-sample data only. Out-of-sample is *frozen* — the harness is not allowed to peek.

We also run an **anchored walk-forward**: train on years one through N, test on year N+1, then extend. We do this for the strongest cells from the in-sample analysis only. The point is to see whether the signal survives multiple non-overlapping forward windows, not just one.

### 3. A Cost-Fuzz Sensitivity Pass

Strategy results in academic papers are sometimes nearly cost-blind. Retail and small-fund execution emphatically is not. So Stage-1 deliberately stress-tests the signal under harsher cost assumptions:

- Spread cost at 1×, 2× and 3× the empirical median spread.
- Overnight financing on or off, using a real broker convention rather than zero.

The cost-fuzz is implemented as a single re-aggregation pass over the same per-period return series — not six full backtest runs. That keeps the runtime sane and the comparison apples-to-apples.

### 4. A Stage-0 Reconciliation Check

The harness reconciles itself against the original Stage-0 result on the cell that overlaps. If the Stage-1 implementation cannot reproduce Stage-0 within a small tolerance, the discrepancy itself is treated as a finding and must be resolved before any Stage-1 verdict is taken.

This is the kind of check that catches silent bugs — a different rebalance day, a subtly different return calculation, an off-by-one in the universe filter. None of those are fraud; all of them quietly invalidate the conclusion if left unchecked.

## What Stage-1 Can Tell You That Stage-0 Cannot

Stage-0 answers: "Is the signal worth our time?" Stage-1 answers a tighter question: "Is the signal still there when we stop letting ourselves cheat?"

Specifically, Stage-1 can detect:

- **Parameter fragility** — the signal works only at one W or one quantile. If the surrounding cells are flat or negative, the "best cell" is almost certainly a fluke.
- **Regime concentration** — the signal earns its full P&L in one or two short periods and bleeds the rest of the time. Walk-forward exposes this directly.
- **Cost sensitivity** — the signal is real at 1× spread but extinguished at 2× or 3×. That is a known-bad outcome for any strategy that has to clear retail or small-fund costs.
- **Anchor non-replication** — the implementation can be made to reproduce the originating paper's claim on its own window, or it cannot. If it cannot, the strategy is filed under "could not replicate the anchor" and we stop.

We have pre-committed thresholds for each of these conditions. None of them are negotiable in the heat of looking at a freshly-rendered backtest chart. Past experience says that *that* is the most important rule in the entire process.

## What Comes Next

The next stages of the pipeline for this hypothesis are mechanical:

- If Stage-1 passes cleanly, the strategy is promoted to Stage-2 — a live-paper deployment at small notional, with execution behaviour, slippage and operational integration treated as the things being tested.
- If Stage-1 is borderline — clears some gates and not others — the result is escalated as evidence for a portfolio-level decision, not auto-promoted.
- If Stage-1 fails, the strategy is killed and filed. The kill is not a failure of the team; it is the system working as designed.

In parallel, the broader research pipeline is building out a curated candidate list of further Stage-1 hypotheses. The same harness will be reused — that is the entire point of building it carefully — across asset classes other than FX. We will write up that selection process separately.

## Why This Pipeline Exists

There is a temptation, when a backtest shows up green, to compress all of this into "we tried it, it worked, we shipped it". That is exactly the path that leads to live capital being committed to overfitted strategies whose real out-of-sample expectancy was always near zero.

The multi-stage falsification pipeline is the answer to that temptation. It is slower. It kills more ideas. It produces fewer headlines. It is also the only honest way we have found to decide what to risk capital on.

For FX reversal specifically, the next interesting public update will be a write-up of the Stage-1 verdict — pass, borderline, or kill — published only once the relevant results have cleared internal review.

---

**Methodology note**: This article describes the design of a multi-stage falsification pipeline for systematic strategy research. Specific Stage-1 in-sample and out-of-sample metrics for the FX reversal hypothesis are intentionally withheld until the underlying analysis is finalised and approved for public release. The Stage-0 academic anchor (FX momentum and reversal literature — see e.g. Menkhoff et al. 2012; Lehmann 1990) and the universe definition (G10 USD pairs on Dukascopy daily data, monthly rebalance) are public.
