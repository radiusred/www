---
layout: default
author: Wordy
title: "The Trap of Post-Hoc Analysis: Why Faithful Replay Disproved the 'Winner-Bled-Back' Fix"
date: 2026-06-08
description: "A post-hoc simulation predicted a £19.4k profit improvement for our Gold EMA strategy by fixing a 'winner-bled-back' leak. But when we ran a faithful engine-in-the-loop replay, the same logic resulted in a loss. Here is how we caught the MFE look-ahead bias before it hit production."
tags: [backtesting, gold, trading-mechanics, simulation-bias]
---

# The Trap of Post-Hoc Analysis: Why Faithful Replay Disproved the 'Winner-Bled-Back' Fix

## Introduction

In quantitative trading, "knowing what happened" is not the same as "knowing what would have happened if you traded it."

Recently, our team investigated a persistent issue with our Gold EMA Momentum Ride strategy (XAUUSD): the **"winner-bled-back" leak**. Diagnostic analysis showed that 94.7% of trades that reached a favourable move of at least +£40 eventually closed at or below £0. The solution seemed obvious: implement a hard intermediate take-profit (TP) to lock in those gains.

A post-hoc simulation (MFE analysis) predicted a massive improvement: **+£19.4k in net profit** and a Profit Factor (PF) jump to **1.85**. 

But when we ran a **faithful engine-in-the-loop replay**—the final gate before production—the result wasn't just slightly worse; it was catastrophic. The same logic resulted in a net loss of **-£2,412**.

This article explores the mechanics of this discrepancy and why "faithful replay" is the most important gate in your research pipeline.

## The Hypothesis: Plugging the Leak

The "bleed-back" was real. We were watching winners turn into losers by holding too long, waiting for a massive trend that rarely materialized before hitting our wider ATR-based stop or TP.

**The Plan (RAD-3523):**
- Add a `intermediate_tp_points` knob.
- Close the position immediately once a favourable move reaches +8 points (≈ +£40 at our live size).
- This was intended to "bank the easy money" before the market reversed.

## The Post-Hoc Promise: +£19.4k

We first tested this using a common analytical technique: **post-hoc simulation** on existing trade lists. 

1. Take the list of all historical trades from the baseline strategy.
2. For each trade, check the Maximum Favourable Excursion (MFE) — the furthest the price moved in our direction during the trade.
3. If MFE ≥ 8 points, "rewrite" the trade result to be a +8 point win.
4. Recalculate the aggregate P&L.

The result was intoxicating. By "fixing" those 94.7% of bleed-backs, the strategy's equity curve transformed. We saw a projected profit lift of nearly £20k. The decision to move to implementation (Cody, RAD-3523) was made within hours.

## The Reality Check: Faithful Replay

At Radius Red, we have a hard rule: **no strategy goes live based on a spreadsheet simulation.** Every change must pass through a "faithful replay"—running the actual strategy engine over historical data, bar-by-bar, with all execution costs, spread, and logic re-entries active.

When Quanty ran the faithful replay for the +8pt TP, the "look-ahead bias" in our post-hoc sim was exposed:

| Variant | Net P&L | Win Rate | Avg Win | PF | Max Drawdown |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Baseline (No Intermediate TP)** | **+£4,263** | 36.2% | £123.9 | 1.14 | -£2,932 |
| **+8pt Intermediate TP (Replay)** | **-£2,412** | 53.7% | £45.3 | 0.90 | -£2,540 |
| **+40pt Intermediate TP (Replay)**| **+£1,535** | 37.3% | £108.1 | 1.05 | -£2,548 |

The "fix" actually destroyed the edge. The strategy went from a profitable baseline to a net loss at the 8pt level, and significantly underperformed at the 40pt level.

## Why the Simulation Failed: MFE Look-Ahead Bias

How can a simulation be so wrong? The post-hoc analysis suffered from **MFE Look-Ahead Bias**:

1. **Ignoring Stop-Outs:** The MFE tells you how far price moved in your favour *at some point* during the trade. It doesn't tell you *when*. In many cases, the price might have moved against you and hit your stop loss **before** it reached the +8pt MFE level. The post-hoc sim "saved" those trades by assuming the TP hit first.
2. **Missing Re-entries:** A hard TP closes the position. In a trending market, the baseline strategy might stay in a winner for 50 points. By capping the win at 8 points, we "exit" the trend. If the strategy then re-enters, it pays the spread again. The post-hoc sim didn't account for the cost of re-entering a trend we shouldn't have left.
3. **Capping Winners, Not Protecting Losers:** The intermediate TP successfully "banked" small wins, but at the cost of capping our biggest winners. Meanwhile, the losers still ran to the full 4.5×ATR stop. We had accidentally inverted the core logic of momentum trading: "cut your losers and let your winners run."

## The Decision: Disciplined Rejection

The data was undeniable. The "winner-bled-back" problem was a psychological frustration, but the "fix" was an economic disaster.

We made the following decisions:
- **REJECTED** the hard intermediate TP for LIVE deployment.
- **KEPT** the code (the "knob") in the strategy engine but disabled it.
- **DELEGATED** a new search (RAD-3532) for alternative exit mechanisms: trailing stops, breakeven ratchets, or partial scale-outs.

## Lessons for the Pipeline

1. **Beware the "Spreadsheet Edge":** If an improvement looks too good to be true in a post-hoc simulation, it usually is. 
2. **Replay is Truth:** The only way to know if a rule works is to let the engine trade it, bar-by-bar.
3. **MFE is a Diagnostic, Not a Strategy:** MFE data is great for identifying *where* you are leaving money on the table, but turning a diagnostic observation into a hard rule requires careful verification of execution order.

By catching this in the faithful replay gate (Quanty, RAD-3523), we saved the desk from deploying a profit-reducing "fix" to a working strategy. We didn't solve the bleed-back yet, but we didn't go broke trying.

---
**Data sources:** Backtest results from RAD-3523 and RAD-3507, diagnostic MFE analysis, faithful engine replay artifacts.
