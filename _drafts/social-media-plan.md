# Social Media Plan (June 2026)

## Week of June 8 - June 12

### Monday, June 8 (Today)

#### LinkedIn (Quant Angle)
**Focus:** Systematic Strategy Identification (Ref: 2026-06-02 blog)

At Radius Red, we don’t just move on to the next idea when a strategy fails our acceptance gates. We use a systematic framework to identify the vacuum left behind and filter new candidates against specific portfolio gaps.

Last week, we open-sourced our thinking on how we move from a "Kill Decision" to "Candidate Identification" using a 180-cell matrix across 30 instruments and 6 archetypes.

Read the full breakdown of how we replaced a failed intraday breakout with a borderline-pass Donchian champion:
https://www.radiusred.uk/blog/posts/2026-06-02-systematic-strategy-identification-after-a-kill/

#systematictrading #algotrading #quant #tradingstrategy #research

---

#### Bluesky (Tech Angle)
**Focus:** The Scale Guard (Ref: 2026-06-05 blog)

Catch up on our latest engineering post: "The Scale Guard That Earned Its Keep".

How a 20-line log-space check caught a 100x notation mismatch between our historical warmup seed and live broker feed. Loud errors at IO seams save days of forensic rework.

https://www.radiusred.uk/blog/posts/2026-06-05-the-scale-guard-that-earned-its-keep/

#algotrading #python #reliability #engineering

---

### Tuesday, June 9

#### Bluesky (Tech Angle)
**Focus:** Data Quality Auditing (Ref: 2026-06-09 blog)

New on the blog: "Auditing a Market Data Cache Before You Trust a Backtest".

Gaps, DST seams, spread anomalies, and cross-provider drift—historical data is usually dirty. Here is the mechanical audit we run on our Dukascopy cache before any result is allowed to matter.

https://www.radiusred.uk/blog/posts/2026-06-09-auditing-a-market-data-cache-before-you-trust-a-backtest/

#dataquality #backtesting #opensource #python

---

### Wednesday, June 10

#### LinkedIn (Quant Angle)
**Focus:** Data Quality (Ref: 2026-06-09 blog)

A backtest is only as honest as the data it touches.

At Radius Red, we assume our historical data is dirty until proven otherwise. We've automated four key checks—session gaps, DST transitions, spread sanity, and stale runs—into a JSON-emitting audit routine.

We’ve just shared the technical details and why auditing the cache is higher leverage than auditing any single backtest.

https://www.radiusred.uk/blog/posts/2026-06-09-auditing-a-market-data-cache-before-you-trust-a-backtest/

#quant #trading #dataquality #fintech

---

### Thursday, June 11

#### Bluesky (Tech Angle)
**Focus:** Connection Resilience (Ref: 2026-06-11 blog)

> **READY TO POST (≤300 graphemes — verified).** This is the version to publish; the longer copy below is reference only.

A running process is not a working process.

A container can report "UP" while blind to the market for 30 min. The layered watchdog we built to make our trading stream self-heal 👇

https://www.radiusred.uk/blog/posts/2026-06-11-a-running-process-is-not-a-working-process/

#reliability #python

(293 graphemes — verified under Bluesky's 300 cap.)

<!-- longer reference draft (exceeds 300 — do not post as single Bluesky post):
"A Running Process Is Not a Working Process." Just published: Why a perfectly "up" container can be quietly blind to the market for 30 minutes, and the layered watchdog approach we built to make our streaming connections self-heal. Featuring: re-auth BEFORE reconnect, unproductive-reconnect caps, blunt safety nets vs. elegant fixes. -->

#reliability #devops #python #algotrading

---

### Friday, June 12

#### LinkedIn (Tech/Process Angle)
**Focus:** Production Resilience (Ref: 2026-06-11 blog)

The word "UP" is a comfortable lie.

We recently hit a failure mode where our trading stack reported perfectly healthy metrics while being blind to the market for half an hour. The transport layer had reconnected, but the session was stale.

We’ve written about the gap between "process running" and "process working", and why we measure liveness at the point of useful work emission.

https://www.radiusred.uk/blog/posts/2026-06-11-a-running-process-is-not-a-working-process/

#reliabilityengineering #systemdesign #fintech #production

---

## Week of June 15 - June 19

### Monday, June 15

#### LinkedIn (Quant Angle)
**Focus:** Systematic Strategy Identification (Follow-up)

#### Bluesky (Tech Angle)
**Focus:** System Health

---

### Tuesday, June 16

#### Bluesky (Tech/Ops Angle)
**Focus:** The Audit Caught Us (Ref: 2026-06-16 blog)

"We wrote a cache audit post. Then our own cache broke."

A story of two bugs, a "successful" routine that was actually failing, and why your liveness probes should measure *results*, not exit codes.

https://www.radiusred.uk/blog/posts/2026-06-16-we-wrote-a-cache-audit-post-then-our-own-cache-broke/

#engineering #postmortem #reliability #python

---

### Wednesday, June 17

#### LinkedIn (Tech/Quant Angle)
**Focus:** The Audit Caught Us (Ref: 2026-06-16 blog)

Last week, our own data audit script found an 18-symbol lag in our cache—while the refresh routine was reporting 100% success. 

It was a classic case of soft-failure masking: individual components behaved correctly, but the overall result was wrong. We’ve shared the post-mortem on why we now assert on *work done*, not just exit codes.

https://www.radiusred.uk/blog/posts/2026-06-16-we-wrote-a-cache-audit-post-then-our-own-cache-broke/

#datagovernance #engineering #quant #fintech

---

### Thursday, June 18

#### LinkedIn (Quant Angle)
**Focus:** Breaking the 0/14 Streak (Ref: Research Breakthrough blog)

A 0/14 conversion rate in a research pipeline isn't a failure—it's a sign that your filters are working.

After 14 consecutive rejections, our research pipeline finally cleared two new macro-inflation hypotheses for Stage-0 backtesting. Here is a look inside our 7-point filter and why we say "no" to most ideas.

https://www.radiusred.uk/blog/posts/2026-06-18-research-breakthrough-0-14/

#research #systematictrading #quant #tradinghypotheses

---

#### Bluesky (Quant Angle)
**Focus:** The 0/14 Graveyard (Ref: Research Breakthrough blog)

"A research pipeline with a 100% conversion rate is just a funnel for noise."

Why we rejected 14 consecutive trading ideas before finally green-lighting two macro-inflation regimes for Stage-0 testing. 

https://www.radiusred.uk/blog/posts/2026-06-18-research-breakthrough-0-14/

#quant #research #algotrading #systematictrading

---

### Friday, June 19

#### Bluesky (Tech Angle)
**Focus:** LLM Sentiment as a Regime Input (Tease)

We’re exploring LLM-generated sentiment as one possible regime input. First gate: data feasibility before any trading claim.

#LLM #AI #quant #research

---

# July 2026 (Deferred)

### Monday, July 6 (Draft)

#### LinkedIn (Quant Angle)
**Focus:** The Trap of Post-Hoc Analysis (Ref: Post-Hoc Replay Trap blog)

A spreadsheet simulation predicted a five-figure profit lift for one of our momentum archetypes. But when we ran a faithful, bar-level engine replay, the projected gain evaporated into a net loss. 

We’ve just shared the story of how we caught "MFE look-ahead bias" in our research pipeline and why "faithful replay" is the final gate every strategy must clear before it touches production.

Read the post:
https://www.radiusred.uk/blog/posts/2026-07-06-post-hoc-replay-trap/

#backtesting #quant #tradingstrategy #fintech

---

#### Bluesky (Tech Angle)
**Focus:** Replay as Truth (Ref: Post-Hoc Replay Trap blog)

"Simulation bias is the silent killer of systematic desks." 

New on the blog: Why a post-hoc MFE simulation predicted a five-figure profit lift while a faithful bar-level replay predicted a loss. How we caught the bias before it hit LIVE.

https://www.radiusred.uk/blog/posts/2026-07-06-post-hoc-replay-trap/

#algotrading #backtesting #python #quant

---

# Fresh Tech Angles — gathered 2026-06-11 (RAD-4162 sweep)

> June blog pipeline is **full** (2/2 this week, 6/6 this month once 06-16 + 06-18 publish).
> These are **July+ blog candidates** plus social-only items. Each screened against the
> live-IP / private-research hard rules. **No measured Sharpe/alpha/P&L for any named strategy
> appears here or may appear in published copy.**

## A. Regime-conditional deployment — the philosophy (QUANT, LinkedIn-lead)
Source: RAD-3970 (design spec), RAD-3987 (primitives), RAD-3988 (validation harness).
**Angle:** "Why we stopped demanding strategies that work in all conditions." An all-weather
robustness bar (PBO/CSCV/regime-robustness) correctly kills overfit — but it also discards
strategies with a *real, regime-conditional* edge, because "works everywhere always" is a tiny,
crowded set. The fix: gate deployment on a regime classifier instead of demanding universality.
**SAFE to tell** as methodology/philosophy. **MUST NOT** include: the live book size, trade
counts, the ARR target, or any per-strategy result figures (all non-public operating data / IP).
Pairs as a follow-up to the published 2026-05-26 regime-conditional-alpha-validation post.

## B. Building a regime classifier with a frozen, versioned taxonomy (TECH, Bluesky-lead)
Source: RAD-3987.
**Angle:** A clean engineering post for the Python/algotrading crowd. Three independent axes —
trend (SMA-slope + ADX), volatility (ATR percentile vs trailing window), carry (financing sign) —
evaluated on **closed bars only** to kill look-ahead, with the taxonomy **versioned and frozen**
(changing it is a release event, not a per-sleeve knob). Great "no-look-ahead by construction"
discussion. No live numbers needed → fully publishable.

## C. Testing the untested entry point: 0% → 70% coverage (TECH, Bluesky)
Source: RAD-101 (session_runners.py).
**Angle:** The integration seam that ran both backtest and live had **0% test coverage**. The
unlock was refactoring for testability — extracting a pure `_resolve_epic_period()` and mocking
the data cache. Relatable Python-testing story; humour angle ("the scariest file in the repo had
no tests"). Fully public.

## D. We deleted 264 GB and slept better (TECH/ops, Bluesky social-only)
Source: RAD-4047.
**Angle:** A research sweep left 264 GB of per-cell intermediate JSONL; the signal was already
preserved in 27 MB of summary CSVs. Deleting the intermediates took disk 86% → ~50%.
Light data-hygiene anecdote. Public — no strategy specifics required.

## E. Risk control: don't open a position you're about to flatten (QUANT/risk, LinkedIn)
Source: RAD-162 (+ RAD-153 close enforcer).
**Angle:** A market-close enforcer flattens open positions before the bell — so opening a new
position 10 minutes before close just burns spread. The fix is an *entry*-suppression window, not
just an *exit* one. Clean risk-control technique. Keep it conceptual (no live window minutes /
instrument-specific params).

## F. Config without a rebuild (TECH/devops, Bluesky social-only)
Source: RAD-140.
**Angle:** A YAML config tweak shouldn't need a 5–15 min image rebuild + redeploy. Pulling
strategy config from object storage at startup cuts the loop to <2 min. Standard but well-told
deployment-architecture nugget. Public.

## Proposed July blog slots (curated — max 2/week, 6/month)
1. **Regime-conditional deployment philosophy** (A) — lead quant piece, abstracted.
2. **Frozen-taxonomy regime classifier** (B) — tech companion, no-look-ahead by design.
3. **0% → 70%: testing the scariest file** (C) — Python testing, light tone.
(D/E/F → Bluesky/LinkedIn social-only unless they grow into a fuller story.)
