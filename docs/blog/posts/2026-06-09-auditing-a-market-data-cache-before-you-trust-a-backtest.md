---
layout: default
author: Wordy
title: "Auditing a Data Cache Before You Trust What's Downstream"
date: 2026-06-09
description: "Downstream analysis assumes the historical data is clean. It usually isn't. Here is the data-quality audit we run on a time-series cache — gaps, DST seams, distribution anomalies, stale records, and cross-provider drift — before any result is allowed to matter."
tags: [engineering, data-quality, open-source]
---

# Auditing a Data Cache Before You Trust What's Downstream

## The unglamorous part of data engineering

Most downstream analyses fail in interesting ways. A result looks compelling, then turns out to have been computed over a slice of data where the underlying feed was wrong. A surprise gap during a DST transition gets papered over by the resampler. A run of stale records inflates a "trend." A vendor quietly shifts a value's scale and the output sails on, indifferent to the fact that one period is no longer comparable to another.

We have made all of those mistakes in our own work at one point or another. The cheapest defence we have found is to assume the data is dirty until proven otherwise, and to run a fixed audit before any historical dataset is allowed to drive a decision.

This article walks through the audit we run against a local time-series cache, the same shape of cache one of our open-source data tools produces. The audit scripts are read-only, deterministic, and intentionally boring. None of this is about any specific analytical edge. It is about making sure a downstream result is at least testing what we think it is testing.

## Why the cache is the right object to audit

The tool is built around a simple shape: download source records once, normalise them into fixed-interval candles, persist them under a cache directory, and then never touch the network during downstream analysis. Everything downstream — resamplers, models, evaluation harnesses — reads from that cache.

That design has two consequences. First, the cache becomes the only thing a downstream result needs to be honest about. Second, a single quiet corruption in the cache can poison every result computed against it from that point forward. Auditing the cache is therefore higher leverage than auditing any single downstream run.

The audit ships as two scripts:

- a fast, local, read-only audit of the existing cache
- a cross-check of the local daily series against independent reference data

Both are meant for maintainers and researchers, not for the normal export path. They emit JSON so the output is easy to diff between snapshots and easy to gate CI or pre-analysis checklists on.

## What the local audit looks for

The local audit reads the cache for a list of series over a year window and emits a per-series report covering four categories.

### 1. Session gaps and the longest intraday gap

A clean fixed-interval feed should have predictable gaps: weekends, calendar holidays, the vendor's maintenance window, and (for some series) session breaks. Everything else is suspicious.

The audit counts intraday gaps over 15 minutes, reports the longest intraday gap with its start timestamp, and excludes obvious weekend gaps so the signal stays useful. A series that suddenly shows a 90-minute hole in the middle of a normally-active session is something a researcher needs to see before they run further analysis on it.

### 2. DST-transition bar counts

Twice a year a fixed-interval bar series picks up an unusual day: one short, one long, depending on which local convention the underlying source follows. Most downstream tools silently swallow this; many resamplers do not.

The audit walks through the relevant DST boundaries and compares the bar count on the transition day (and the day after, where drift typically shows up) against an expected baseline. The output is intentionally a soft signal — DST anomalies are not always bugs, but they are always worth eyeballing before treating that window as flat data.

### 3. Distribution sanity

For each bar with both a low and high value we compute a spread, then summarise the distribution: median, 5th percentile, 95th percentile, 99th percentile, count of impossible (zero-or-negative) spreads, and count of "extreme wide" bars where the spread is more than ten times the 95th percentile.

This is the check that has caught us the most surprises. A handful of impossible spreads usually means a one-sided data run, easy to handle. A spike in extreme-wide bars during a specific date range usually means we are looking at a series that was thinly reported during that period, and any analysis run over that window will overstate quality unless the cost model is honest about it.

### 4. Stale records

Some series occasionally print the same level for many consecutive minutes during quiet periods. The audit flags runs of stale values so that we know whether a "low-activity" period in the data was real or a vendor quirk.

Each of these four checks is one short, dataclass-based function in the repo. None of them try to be clever. The point is that the answers exist as numbers in a JSON file, and that we look at them before we look at anything downstream.

## Cross-checking against an independent provider

A local audit can only tell you whether the cache is internally consistent. It cannot tell you whether the cache is right. For that, the second script compares the local daily close series against independent references from other public sources.

It walks the date window day by day, joins on calendar day, computes a percentage delta, and reports counts of days where the local series disagrees materially with the reference. Persistent drift in one direction is the symptom that matters; isolated single-day spikes are usually just two providers disagreeing on which record is "the" close for a thinly-reported period.

This is the script that catches the scariest class of problem: a vendor quietly changing how it represents a value. We have seen that exactly once, and the cross-provider check is now the reason we expect to catch it the next time within a single audit cycle rather than a quarter into a downstream analysis series.

## Where these scripts fit in the workflow

The tool is explicit that it is a data preparation component, not a runtime one. The intended loop is:

1. Download and export historical data once.
2. Commit or archive the output plus metadata.
3. Run fast, deterministic downstream analysis against local files.

The audit sits between steps two and three. Concretely, in our process the gate looks like this:

- A new series lands in the cache.
- Before the first hypothesis is run against it, we execute the local audit over the full available window for that series.
- We run the cross-provider check on the same window.
- The combined JSON output is treated as part of the data provenance for any research note that uses that series.

The audit costs minutes. The alternative — discovering halfway through a parameter sweep that the value scale flipped on a single series years ago — costs days of rework, and worse, costs trust in every result that touched the bad data.

## What the audit deliberately does not do

A few things the audit explicitly does not try to solve, because we have learned that being honest about them is more useful than pretending:

- It does not produce a single pass/fail verdict. Data quality is a distribution, not a boolean. Researchers read the JSON.
- It does not fix the cache. The script ships read-only on purpose; repairing the cache is a separate, deliberate action.
- It does not replace cost or noise modelling. A clean distribution is necessary but not sufficient.
- It does not certify a result. It only certifies that the dataset is not obviously broken.

The framing we use internally: the audit is not the test, it is the precondition for any test being meaningful.

## Borrowing this for your own pipeline

If you are running your own analysis stack against vendor time-series data, the cheap version of this discipline is:

- Pin every dataset to a cache and never download mid-analysis.
- Pick four or five mechanical sanity checks (gaps, DST seams, distribution sanity, stale runs, cross-provider drift) and run them per-series, per-window.
- Emit JSON, not prose. Diff successive audit snapshots. Promote a regression in any of these counters to a research blocker, not a research footnote.
- Make the audit cheap enough that nobody is tempted to skip it.

The bigger point is the habit: a downstream result is only as honest as the data it touched, and the only way to know whether the data was honest is to look.
