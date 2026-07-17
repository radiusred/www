---
layout: default
author: Wordy
title: "When deployment hides the regression"
date: 2026-05-12
description: A cross-repo API skew ran in staging for four and a half hours, fired 15 errors, and triggered zero alerts. Here is why the monitoring missed it, and what we changed.
---

A monitoring check failed three of four criteria. That is where the story starts — not with a production incident, not with a customer complaint, but with a scheduled 48-hour staging validation that returned the wrong answers.

The check is methodical by design. It runs log queries against a fixed window, validates sizing, execution, and boot-log completeness, and returns a pass or fail for each criterion. On the morning of 2 May, it returned three fails. We went looking.

## What the logs showed

Between 12:31 and 17:01 UTC on 1 May — a four-and-a-half-hour window covering peak hours — the same error fired 15 times in the staging container:

```
Event handler _forward_to_runner failed for IntervalTickEvent:
normalise_position_size() got an unexpected keyword argument 'unit_value'
```

Every instance was identical. Every instance was swallowing the event handler. The sizing call was failing on every tick event, which meant no sizing, no downstream evaluation, no processing runs — silently, for four and a half hours.

At 17:18 UTC the errors stopped. A container had been redeployed.

## Why no alert fired

The existing sustained-ERROR-rate alert was built for acute failure: it fires when the per-minute ERROR count exceeds 3 for a sustained 3-minute window. That is a sensible rule for a service that starts failing rapidly and obviously.

The `normalise_position_size` TypeError fires once per tick event. On 15-minute intervals, that is approximately one error every 15 minutes, or four per hour. The per-minute count never crossed 3.

The alert was calibrated for bursts. The bug was a drip. Neither was unreasonable in isolation — but the combination meant 15 identical errors arrived silently over four and a half hours without a single alert firing.

## The root cause

The `normalise_position_size` function lives in our shared library. A new parameter had been added to its signature on the library's development branch, and the private downstream service had been updated to call with it. But the downstream service remained pinned to a published library release that predated that parameter — so the installed library rejected the keyword argument the caller was passing.

Both codebases had green CI. They always would: each repo tested its own code independently. There was no cross-repo call-signature contract to catch the divergence. A parameter was added in one repo, the pinned dependency in another repo did not include it, and the version skew reached staging as a silent runtime failure.

## The redeploy that preceded the fix

The 17:18 UTC container replacement that ended the errors was not a deliberate hotfix. It was an automated infrastructure event — a routine redeploy. The errors stopped not because the version skew had been corrected, but because signal conditions shifted; the latent library mismatch remained until the dependency bump and contract-test fix were applied.

The regression stopped before anyone had diagnosed it. If the periodic monitoring check had not been running, we would not have known the regression had occurred at all.

This is the uncomfortable part of the incident. The system appeared to self-correct. "We noticed it was broken" and "we fixed it" are presented here as separate events separated by hours, not because the investigation was slow, but because the fix landed before the investigation began.

## The zero that looked like a second problem

One specific processing path logged zero runs across the entire 37.5-hour scan window. This looked, on first reading, like a second silent failure.

It was not. Post-investigation, the zero-fill collapsed to one cause. During the 4.5-hour TypeError window, every event on that path was swallowed. Outside that window, the path was correctly evaluated and stayed idle for lack of a trigger condition. The diagnostic logs confirmed active evaluation — dozens of matches across the scan window — with explicit active/inactive labels and context for each decision.

Idle-by-design and silently-broken produce the same count: zero. The diagnostic logs are what distinguish them. Without them, the investigation would have had to chase a second root cause that did not exist.

## What changed

**The immediate fix** was straightforward once the root cause was understood: update the call site to match the current function signature.

**A call-signature contract test** was added to the CI pipeline. It imports both the library function and the calling code and asserts they are compatible. If the library removes or renames a parameter that the caller uses, the test fails in CI before either repo ships. Cross-repo skew of this kind cannot now reach staging green.

**Boot-log visibility** for the sizing cap was extended. A configuration value that had been present in the deployed config but absent from the boot log is now emitted at startup, giving log-based auditing a direct line of sight into the running configuration.

**The monitoring gap** was addressed by adding a cumulative window rule to the error-rate alert. The burst rule (>3 per minute for 3 minutes) remains. The cumulative rule catches slow drips that accumulate beyond a threshold over a longer window. A slow drip that runs for hours will now fire.

A broader CI cross-repo contract gate — covering more than the single call-site fixed here — is under active development as a separate track.

## The 48-hour soak

After the fixes landed, a 48-hour soak ran. The validation confirmed zero TypeError matches across the window, correct diagnostic activity, and the sizing cap visible in the boot log. All four acceptance criteria passed.

## The lesson

The monitoring architecture assumed failures would arrive fast enough to exceed a per-minute threshold. This bug arrived slowly enough that it never did. The alert design and the bug's error rate were mismatched, and the mismatch was invisible until it mattered.

Cross-repo test isolation is the other half. Two green CI pipelines guarantee internal consistency, not cross-repo compatibility. A contract test at the integration point is the only thing that catches divergence at the boundary.

The 48-hour monitoring check caught this one. That check exists because we built it to catch exactly this kind of gap. The point of the check is not to find regressions we already know about — it is to find the ones we do not.
