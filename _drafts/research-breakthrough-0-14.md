---
layout: default
author: Wordy
title: "Breaking the 0/14 Streak: Inside the Rigorous Filter for New Trading Hypotheses"
date: 2026-06-08
description: "After 14 consecutive rejections, our research pipeline finally converted two new hypotheses for Stage-0 backtesting. Here is why most ideas fail our 7-point filter and what it takes for a new macro-regime strategy to break through."
tags: [research, systematic-trading, quant-analysis, inflation]
---

# Breaking the 0/14 Streak: Inside the Rigorous Filter for New Trading Hypotheses

## Introduction

At Radius Red, the barrier for a new trading idea to reach "Stage-0" backtesting is intentionally high. 

Recently, our research assistant, Scout, and quantitative specialist, Quanty, hit a remarkable streak: **14 consecutive rejections**. Fourteen well-researched, academically-backed ideas were archived without a single line of backtest code being written.

Last week, the streak finally broke. Two new hypotheses—both based on macro-inflation regimes—cleared the filter.

This article pulls back the curtain on our **7-point Research Filter** and explains why "good ideas" are often "bad candidates" for a systematic trading desk.

## The 0/14 Graveyard: Why Most Ideas Fail

The 14 rejected ideas weren't "bad." They came from top-tier sources like SSRN, arXiv, and respected practitioners. However, they fell into three recurring traps:

### 1. The "Network of One" Problem (Data Feasibility)
Several interesting archetypes—**Network Momentum** (lead-lag effects) and **Intra-Market Correlation**—were rejected because they required a cross-section of 10–20 liquid commodity instruments. Our current high-quality data cache is focused on 3 FX pairs and Gold (XAUUSD). 
*   **The Lesson:** A "network momentum" strategy on a "network of one" is just a trend-follower in disguise. If we can't build the cross-section, we can't test the mechanism.

### 2. The "Re-Killing" Trap (Anchor Non-Replication)
Scout surfaced multiple high-quality papers on **FX Session Breakouts** (London/Tokyo open patterns). These were rejected because our kill ledger (the "black book" of failed tests) already contains exhaustive results for these archetypes on EURUSD and USDJPY.
*   **The Lesson:** A new regime overlay on a dead archetype doesn't make it a new mechanism. Unless the paper identifies a fundamentally different *reason* for the move, we don't re-test what we've already killed.

### 3. "Parameter-Fuzz" on Kept Anchors
Hypotheses that were essentially "Gold EMA, but with a different lookback" or "Trend-following, but with Kelly sizing" were archived. 
*   **The Lesson:** We already have a "kept anchor" for Gold Trend-Following. Improving it is an optimization task for Cody and Quanty, not a new research hypothesis for Scout. We save Stage-0 slots for **new signals**, not just new parameters.

## The Breakthrough: Inflation as a Regime Gate

The streak broke with two companion papers by Vojtko & Dujava (Feb 2025) that targeted a specific gap in our portfolio: **Macro-Regime Filters**.

**The Winners:**
1.  **RAD-3603 (Gold Inflation Regime):** Using CPI month-over-month trends as a gate for Gold momentum.
2.  **RAD-3604 (USD Inflation Direction):** Using CPI trends to drive USD direction across major FX pairs.

## Why These Passed the 7-Point Filter

| Filter Point | Why it Passed |
|:---|:---|
| **F1: External State** | Trade triggers are driven by **CPI releases** (macro data), not just price action. |
| **F2: Cost Economics** | Low-turnover regime switches (monthly) easily clear the hurdle of IG's CFD carry costs. |
| **F3: Persistence** | The inflation regime (2 consecutive months of change) provides a stable backdrop for trading. |
| **F5: Low Turnover** | Monthly rebalancing minimizes spread bleed. |
| **F6: Non-Replication** | We have no existing macro-inflation strategies; these are orthogonal to our current trend and MR sleeves. |
| **F7: Horizon** | The expected hold period is months, well above our 12-bar minimum floor. |

## The Outcome: Stage-0 Active

These two hypotheses have now advanced to **Stage-0**. Cody will build the data ingestion for CPI macro-indicators, and Quanty will run the first discovery backtests.

The success of these candidates wasn't accidental. It was the result of Quanty "tightening the leash" on Scout, forcing a pivot away from practitioner aggregator blogs and toward **primary academic sources with slow-moving external states.**

## Conclusion: The Value of "No"

A research pipeline with a 100% conversion rate isn't a pipeline; it's a funnel for noise. 

The 14 rejections were as valuable as the 2 promotions. They ensured that the engineering and analysis budget wasn't wasted on "look-alike" strategies or data-infeasible models. By being disciplined enough to say "no" to Carver-style trend replication and intraday session breakouts, we kept the desk focused on the one thing that matters: **finding uncorrelated, fundamentally-driven alpha.**

---
**Data sources:** Scout's curated research bucket (`curated_sources.json`), Quanty's review log (RAD-3458 to RAD-3602), 7-point filter definitions in AGENTS.md.
