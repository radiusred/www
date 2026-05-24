---
layout: default
author: Wordy
title: "Introducing tradedesk-miner — a fast Rust scanner for our Dukascopy cache"
date: 2026-05-29
description: "tradedesk-miner is a new open-source Rust binary we use to scan our cached Dukascopy candle data for statistical anomalies, cross-instrument relationships, and seasonality effects. v1.0.2 ships prebuilt binaries and emits results as a locked NDJSON envelope you can pipe straight into a research agent."
tags: [engineering, open-source, market-data, rust, tradedesk-miner]
---

# Introducing `tradedesk-miner` — a fast Rust scanner for our Dukascopy cache

## The gap this fills

We have spent the last few months on the same broad project: turn years of cached Dukascopy candle bytes into a steady, honest stream of testable trading hypotheses. Two of the supporting tools were already public.

[`tradedesk-dukascopy`](https://github.com/radiusred/tradedesk-dukascopy) fetches and normalises the raw ticks into a deterministic on-disk cache. [`tradedesk`](https://github.com/radiusred/tradedesk) takes a candidate strategy and turns it into a reproducible backtest or live run. The piece in the middle — the one that systematically reads the cache, runs a broad sweep of statistical tests, and flags candidate effects worth turning into hypotheses — was an internal tool until last week.

It is now public. Today's release is [`tradedesk-miner v1.0.2`](https://github.com/radiusred/tradedesk-miner/releases/latest).

```
tradedesk-dukascopy (cache)  →  tradedesk-miner (raw findings)
                             →  research agent (hypotheses)
                             →  tradedesk (backtests, live)
```

## What it ships in v1.0

The v1 scan engine ships 23 scans across three families, each with a frozen behaviour contract:

- **Single-instrument anomalies** (12 scans). Returns profile, Welford moments, rolling volatility and vol-of-vol, Ljung–Box on returns and squared returns, ADF, KPSS, Lo–MacKinlay variance ratio, ARCH-LM, Jarque–Bera, z-score and MAD outlier detection, and a drawdown profile.
- **Two-instrument cross-relationships** (5 scans). Rolling Pearson and Spearman correlations, rolling OLS β, cross-correlation lead/lag, and Engle–Granger cointegration with an Ornstein–Uhlenbeck half-life estimate.
- **Seasonality** (6 scans). Hour-of-day, day-of-week, session, end-of-month and start-of-month buckets, an ANOVA + Kruskal–Wallis bundle, and an event pre/post-window scan.

The full catalogue, including each scan's inputs and outputs, lives in [`docs/scan_catalogue.md`](https://github.com/radiusred/tradedesk-miner/blob/main/docs/scan_catalogue.md) in the upstream repo.

A `sweep` runner stacks these into batches via a small TOML manifest, applies bootstrap confidence intervals, builds a null distribution, and corrects multi-test inflation with the Benjamini–Hochberg false-discovery procedure. The sweep grammar is documented in [`docs/sweep_manifest.md`](https://github.com/radiusred/tradedesk-miner/blob/main/docs/sweep_manifest.md).

## The output contract

The piece we are most pleased about is the output envelope, which is intentionally simple.

`miner` writes a single locked JSON shape called a `Finding` to stdout, one envelope per line. Logs and progress go to stderr. The envelope is a tagged enum with seven variants — `run_start`, `result`, `scan_error`, `gap_aborted`, `dry_run`, `sweep_summary`, `run_end` — and the schema is additive only. The ground truth lives at [`schemas/findings-v1.schema.json`](https://github.com/radiusred/tradedesk-miner/blob/main/schemas/findings-v1.schema.json).

Why we cared enough to lock it: every downstream consumer can be a simple subprocess-and-stream-parse. No RPC. No new wire format. No "logging shape that quietly drifted between releases." Re-running with the same seed against the same revision and cache produces byte-identical NDJSON once four volatile fields — `run_id`, two timestamps, and `wall_clock_ms` — are masked. That property is what lets us put miner output into a research pipeline and trust diffs across runs.

A truncated `result` envelope looks like this:

```json
{
  "kind": "result",
  "scan_id@version": "stats.autocorr.ljung_box@1",
  "effect": {
    "metric": "ljung_box_q_stat",
    "value": 33.87,
    "p_value": 0.043,
    "extra": { "lags": 10, "acf": ["…"] }
  },
  "data_slice": { "sources": [ { "symbol": "EURUSD", "side": "bid" } ] }
}
```

The full envelope reference is in [`docs/findings_envelope.md`](https://github.com/radiusred/tradedesk-miner/blob/main/docs/findings_envelope.md).

## Speed

The reason this is a Rust binary and not "just another Python script" is that the cache is large enough — single-digit gigabytes of compressed candles per instrument-year — that interpretation overhead starts to dominate. The `miner-core` engine is sync code on top of [rayon](https://github.com/rayon-rs/rayon) work-stealing; async only lives at the wrapper edges. There is no `tokio` in the core, and there is a CI gate that prevents one creeping in.

In practice, on a single-instrument month of 15m candles, a typical scan completes in well under a second on a developer workstation; cross-instrument scans (cointegration, lead/lag) over a few months of 1h data tend to land in the low single-digit seconds. We are intentionally not publishing a headline wall-clock number in this post — the canonical, per-revision figures live in the bench doc described below, captured on a reference workstation with a frozen recipe so the numbers are reproducible rather than anecdotal.

For context, we use these scans not to make trading decisions but to identify candidate effects to study further. At sub-second-to-a-few-seconds per scan, an analyst (or, in our case, a research agent) can comfortably run a sweep across a few dozen instruments and timeframes during the time it takes to make a cup of tea, then spend the rest of the morning deciding which findings are worth a hypothesis. The performance budget exists so that the *thinking step* downstream of the scan does not have to compete with the scan itself for wall clock.

The published binaries are around 8 MiB stripped per platform. The reference workstation, the allocation budget, and the reproducible recipes under `benches/recipes/*.toml` are all documented in [`docs/bench-results.md`](https://github.com/radiusred/tradedesk-miner/blob/main/docs/bench-results.md); concrete capture numbers will be filled into that doc per release rather than embedded in the README or a blog post, so they can age out cleanly.

## How to install it

The release process publishes prebuilt binaries — and verifiable SHA256 checksums — to the [GitHub Releases page](https://github.com/radiusred/tradedesk-miner/releases/latest). This is the key difference from `tradedesk` and `tradedesk-dukascopy`, which ship to PyPI: `tradedesk-miner` is a Rust binary you drop onto `$PATH`, not a `pip install`. There is no toolchain requirement on the consumer side.

Targets currently published per release: `x86_64-unknown-linux-gnu`, `aarch64-unknown-linux-gnu`, `x86_64-apple-darwin`, `aarch64-apple-darwin`.

```sh
# Substitute the asset for your platform and verify it against the
# release's SHA256SUMS file before extracting.
curl -fsSL -O https://github.com/radiusred/tradedesk-miner/releases/latest/download/SHA256SUMS
curl -fsSL -O https://github.com/radiusred/tradedesk-miner/releases/latest/download/miner-1.0.2-x86_64-unknown-linux-gnu.tar.gz
shasum -a 256 -c SHA256SUMS --ignore-missing
tar -xzf miner-1.0.2-x86_64-unknown-linux-gnu.tar.gz
install -m 0755 miner-1.0.2-x86_64-unknown-linux-gnu/miner ~/.local/bin/miner
miner --version
```

If you do want to build it from source — for instance to hack on a new scan — Rust 1.85 stable is the only prerequisite and the repo's `CONTRIBUTING.md` covers the local quality gates the upstream CI mirrors.

## A first run against a synthetic cache

The repo ships a deterministic synthetic-cache *generator* rather than the cache bytes themselves (we are not in the business of redistributing licensed market data). That means a fresh clone is one script away from a runnable scan:

```sh
bash scripts/generate-fixture-cache.sh
```

That populates `./tests/fixtures/cache/EURUSD/…` and `…/GBPUSD/…` with byte-identical synthetic candles and writes a `SHA256SUMS` manifest you can re-verify any time. The bytes are reproducible across machines via a Numerical Recipes LCG plus single-threaded `zstd-3`, so a "did the cache regenerate cleanly?" check is just one `sha256sum -c`.

Then run a scan and stream NDJSON `Finding` envelopes to stdout:

```sh
MINER_CACHE_ROOT=./tests/fixtures/cache \
MINER_BAR_CACHE_ROOT=/tmp/bar \
MINER_OUTPUT=stdout \
miner scan seas.bucket.hour_of_day@1 \
    --instrument EURUSD:bid --timeframe 15m \
    --window 2024-01-01:2024-01-31
```

Production-shape sweeps use the same CLI plus a TOML manifest — see [`docs/agent_integration.md`](https://github.com/radiusred/tradedesk-miner/blob/main/docs/agent_integration.md) for the full programmatic-consumption walkthrough, including the exit-code routing rules a calling process should rely on.

## Where this fits in the broader open-source stack

The point of releasing miner now, rather than leaving it inside our research environment, is that the other two open-source tools were doing slightly more work than they should: `tradedesk-dukascopy` was being asked "what's *interesting* in this cache?" by people, and the framework around `tradedesk` was quietly accumulating discovery scripts that did not belong there. Splitting discovery out into its own binary with a locked envelope means each of the three projects can do exactly one job, and the integration contract between them is a stable JSON schema rather than tribal knowledge.

If you maintain a market-data cache in a similar shape — bid/ask candles per instrument, organised by year and month — and you are trying to keep your research pipeline honest about what it is testing, miner may save you the time of writing the scanning layer yourself.

If you would rather just read the code, it is [Apache 2.0 on GitHub](https://github.com/radiusred/tradedesk-miner). Issues and ideas welcome.
