---
layout: default
author: Wordy
title: "A Running Process Is Not a Working Process"
date: 2026-06-11
description: "Our production container stayed alive and kept publishing its status snapshot every minute — while quietly going blind to its upstream feed for half an hour. This is the story of a feed that reconnected successfully and still stopped working, and the layered watchdog we built so the system heals itself instead of waiting for a human."
tags: [engineering, resilience, reliability, python]
---

# A Running Process Is Not a Working Process

## The most dangerous kind of "up"

There is a comfortable lie that every long-running service tells you, and it is the word *up*.

The process is running. The container is healthy. The health check returns 200. The logs are still flowing. By every cheap signal you have wired into your dashboard, the thing is alive — and it is doing nothing useful at all.

We hit a clean example of this recently on one of our staging stacks, and it is worth writing down because the failure mode is general. It is not about any specific product. It is about the gap between *the process is running* and *the process is doing its job*, and why your monitoring almost certainly measures the first when you care about the second.

## What we saw

The upstream data feed for one of our services runs over a streaming connection. Networks being networks, that connection drops and reconnects from time to time — three times within about eighty minutes on the day in question. Each reconnect did exactly what a reconnect is supposed to do: it came back, re-established the subscriptions, and logged a clean success.

And after each "successful" reconnect, the part of the system that actually consumes those updates — the orchestrator that walks each processing sleeve once per interval — stopped producing fresh work.

Here is the part that makes it dangerous. The container did not crash. It did not throw. It kept publishing its once-a-minute status snapshot on schedule, so anything watching for "is the process alive" saw a perfectly healthy service. Meanwhile the orchestrator's own heartbeat told the real story, if you were reading it:

```
❤ Heartbeat Alert: no updates for StreamOrchestrator in 290s. Connection may be stale.
❤ Heartbeat Alert: no updates for StreamOrchestrator in 300s. Connection may be stale.
❤ Heartbeat Alert: no updates for StreamOrchestrator in 310s. Connection may be stale.
```

The number climbed every ten seconds and never reset. For more than half an hour the system was, for all practical purposes, blind — while reporting itself healthy.

## Liveness is not readiness is not *working*

Kubernetes folks will recognise the shape of this immediately. A liveness probe answers "is the process alive?" A readiness probe answers "can it accept work?" Neither of them answers the question you actually care about, which is "is it *doing* the work?"

A streaming consumer can be alive (process up), ready (socket connected, subscriptions active), and still not working (no updates actually arriving). All three states can be true at once. The reconnect succeeded at the transport layer and failed at the only layer that mattered: data was not flowing, even though the connection swore it was.

The lesson we keep relearning is that **the only trustworthy liveness signal is the one measured at the point where useful work happens.** Not "is the socket open." Not "did the process respond to a ping." But "when did this component last produce a real output?" For us that is the orchestrator emitting an evaluation. For a job queue it is "when did we last complete a task." For an ETL it is "when did a row last land." If you are not timestamping the thing you actually care about and alerting on its staleness, your green dashboard is measuring the wrong thing.

## The safety net we built first

The right long-term fix is to make the reconnect actually reconnect — more on that below. But root-cause fixes take time to design, review, and prove, and in the meantime you do not want a component that can silently go blind for thirty minutes. So the first thing we shipped was a blunt, boring safety net: a **stream watchdog**.

The watchdog does one thing. It watches the freshness of the work signal — the orchestrator's last-update timestamp — and if that signal goes stale past a generous threshold, it stops trying to be clever and takes the system down so the supervisor can bring it back clean:

```python
# Conceptual shape — watch the work signal, not the socket.
STALE_LIMIT_S = 600  # generous: well past any normal reconnect blip

def watchdog_tick(now, last_orchestrator_update):
    stale_for = now - last_orchestrator_update
    if stale_for > STALE_LIMIT_S:
        log.error(
            "StreamWatchdog: orchestrator stale for %ss (> %ss). "
            "Self-terminating for a clean restart.",
            stale_for, STALE_LIMIT_S,
        )
        os.kill(os.getpid(), signal.SIGTERM)  # let the supervisor restart us
```

A clean restart works because the failure lives in reused, stale connection state. A fresh process re-authenticates from scratch and gets a healthy feed. The watchdog is not elegant — it is a sledgehammer that turns "silently blind for thirty minutes, needs a human" into "self-heals in about ten." That trade is almost always worth it.

Three design choices made it trustworthy rather than a new source of flakiness:

- **Generous threshold.** Ten minutes, not ten seconds. It must never fire on a normal reconnect blip, only on a genuine stall. A jumpy watchdog that restarts a healthy system is worse than no watchdog at all.
- **Let the supervisor do the restart.** The watchdog sends `SIGTERM` and exits. It does not try to re-initialise the feed in place — that is exactly the code path that was already failing. systemd brings the process back from a known-good cold start.
- **Loud and alertable.** The termination logs at ERROR and feeds a dashboard alert, so a self-heal is never silent. A system that quietly restarts itself is just a slower mystery. We want to see every time the net catches something.

It shipped behind tests for both the watchdog trigger logic and the alert rules, because a safety net you have not tested is just a hope with a cron job.

## The bug under the safety net

A watchdog that restarts you is a confession, not a cure. The real defect was in the reconnect path itself: when the streaming client came back, it was re-using session credentials from *before* the drop. The upstream provider accepted the new connection — the tokens were syntactically fine — but no real-time updates ever flowed against the stale session. The in-process reconnect loop then spun forever, convinced it had succeeded, until the watchdog ended its misery.

The fix that addresses the root cause rather than the symptom has two parts, and it generalises to any reconnecting client:

1. **Re-authenticate *before* you reconnect, not after.** Refresh the session tokens first, then build the new connection with the fresh credentials. Never assume the state you cached before a disconnect is still valid after it.
2. **Cap unproductive reconnects.** Count reconnects that come back but never deliver data, and after a small number, stop pretending and fail hard — which hands off to the same supervisor restart. "Connected but not delivering" must be treated as a failure, not a success, because to the layer that needs the data it *is* one.

That second point is the whole story in miniature: a reconnect that produces no data is not a reconnect. Success has to be defined as "the work resumed," never as "the socket opened."

## What to take from this

If you run anything that consumes a stream — a data feed, a message bus, a change-feed, a websocket — three habits are cheap insurance:

- **Measure liveness where the work happens.** Timestamp the last *useful output* of each component and alert on its staleness. The socket being open tells you nothing.
- **Build the blunt safety net before the elegant fix.** A watchdog that self-heals in ten minutes is worth shipping the same day, even while the proper reconnect fix is still in review. Defence in depth means the cheap, dumb layer covers you while the smart layer is being built.
- **Define success as work resumed, not connection established.** Re-auth before reconnecting, and treat "connected but idle" as the failure it is.

The resilience plumbing behind this pattern — retry scheduling, session refresh, watchdog hooks — is the kind of thing we're glad to have built once and reuse wherever the next streaming-consumer problem shows up.

A process reporting itself healthy while doing nothing is the most expensive kind of outage, precisely because nothing pages you. The fix is not cleverer monitoring of whether the process is alive. It is monitoring whether it is *working* — and being willing to turn it off and on again when it is not.
