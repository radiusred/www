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

"A Running Process Is Not a Working Process."

Just published: Why a perfectly "up" container can be quietly blind to the market for 30 minutes, and the layered watchdog approach we built to make our streaming connections self-heal.

Featuring:
- Re-auth BEFORE reconnect
- Unproductive-reconnect caps
- Blunt safety nets vs. elegant fixes

https://www.radiusred.uk/blog/posts/2026-06-11-a-running-process-is-not-a-working-process/

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
**Focus:** The Trap of Post-Hoc Analysis (Ref: Gold EMA Replay Trap blog)

A spreadsheet simulation predicted a £19.4k profit lift for our Gold EMA strategy. But when we ran a faithful, bar-level engine replay, the result was a net loss. 

We’ve just shared the story of how we caught "MFE look-ahead bias" in our research pipeline and why "faithful replay" is the final gate every strategy must clear before it touches production.

Read the post:
https://www.radiusred.uk/blog/posts/2026-06-15-gold-ema-replay-trap/

#backtesting #quant #tradingstrategy #gold #fintech

---

#### Bluesky (Tech Angle)
**Focus:** Replay as Truth (Ref: Gold EMA Replay Trap blog)

"Simulation bias is the silent killer of systematic desks." 

New on the blog: Why a post-hoc MFE simulation predicted £19k in profit while a faithful bar-level replay predicted a loss. How we caught the bias before it hit LIVE.

https://www.radiusred.uk/blog/posts/2026-06-15-gold-ema-replay-trap/

#algotrading #backtesting #python #quant

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
**Focus:** LLM Sentiment for Gold (Tease)

We’re experimenting with ChatGPT-generated sentiment indices as a regime gate for XAUUSD. It just cleared our "data feasibility" filter. 

More on the ML roadmap soon.

#LLM #AI #quant #gold
