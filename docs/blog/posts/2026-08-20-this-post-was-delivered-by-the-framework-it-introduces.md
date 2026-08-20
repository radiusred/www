---
layout: default
author: Cody
title: "This Post Was Delivered by the Framework It Introduces"
date: 2026-08-20
description: "CodeCrew is our lightweight framework for agent-driven software delivery: a thin CLI, four role contracts, and the conviction that GitHub itself is the only message bus a software crew needs. It has now delivered three milestones of its own development — and this post, which arrived on this site as a task issue, an agent-authored pull request, and a human review, exactly the way it tells everyone else to ship."
tags: [engineering, agents, codecrew, open-source]
---

# This Post Was Delivered by the Framework It Introduces

This post started life as [an issue](https://github.com/radiusred/www/issues/41) on this website's repository. An implementer agent wrote a plan into the issue body, a CLI verb refused to let work begin until that plan existed, the text you are reading arrived as a pull request authored by a GitHub App identity called [`radiusred-cody`](https://github.com/apps/radiusred-cody), and a human reviewed and merged it. Every one of those steps is on the public record, and none of them was optional.

The thing that made all of that happen is [CodeCrew](https://github.com/radiusred/gh-codecrew), and this post is its introduction.

## What it is

CodeCrew is a lightweight framework for agent-driven software delivery. Concretely it is three small things:

- **A CLI** — a single Go binary, installable as a GitHub CLI extension (`gh extension install radiusred/gh-codecrew`), with seven verbs: `status`, `milestone new`/`close`, `task new`/`start`/`finish`, and `checkpoint`.
- **Four role contracts** — short markdown files defining what an implementer, a reviewer, a QA agent, and a doc-synthesizer each read, write, and must never do. Any harness that can run a CLI and read markdown can staff a role.
- **A set of conventions on plain GitHub** — issues, sub-issues, labels, comments, and pull requests, arranged so that project state is *inferred* from them rather than bookkept anywhere else.

There is no server, no database, no message bus, and no orchestrator. The inter-agent protocol is GitHub itself: two agents on entirely different harnesses interoperate because they both read and write the same issues and PRs. A hub repository holds the roadmap, milestone tracking issues, and role contracts; any number of spoke repositories hold the actual work, each carrying a two-line pointer file back to its hub.

## Why we built it

Radius Red runs engineering ventures staffed by AI agents. Agents turn out to be good at doing work and unreliable at *process*: remembering to write the plan down, recording why a decision went the way it did, not marking their own homework. Every one of those failures is invisible on the day it happens and expensive months later, when someone asks why the system behaves the way it does and the honest answer is gone.

CodeCrew's position is that process discipline should be mechanical, not aspirational. The verbs refuse. `task start` refuses to begin a task whose issue has no plan. `task finish` refuses to merge without green checks and an approval from someone who is not the author — and refuses, too, if a human decision gate was raised on the task and resolved without the decision being written down. `milestone close` refuses until every requirement carries an independent QA verdict of *satisfied*, and refuses to close at all until the milestone's "why" document — synthesized from the decision records, never reconstructed from memory — is merged. Each refusal is machine-readable (`refused[NO_PLAN]`, `refused[VERDICT_MISSING]`, …), so an agent that hits a gate knows exactly which condition is unmet rather than parsing an error message meant for humans.

Attribution is mechanical too. Each role acts as its own GitHub App, so every commit, comment, and review on the record says which member of the crew did what. The implementer that wrote this post cannot approve its own pull request; the QA agent that audits the milestone containing it must not fix what it finds, only report it.

## Eating the cooking

CodeCrew has now delivered three milestones of its own development, which means every mechanism above earned its place by failing us first in miniature. The hand-maintained task checklist rotted the first time a tick was forgotten, so task tracking moved to GitHub sub-issues and the checklist was deleted. A decision made at a human gate went missing from the milestone record because it was written as free prose, so gate resolutions became structured and enforced. Our favourite: the first QA dispatch found the README claiming "not yet here: a QA agent dispatch history" — a sentence falsified by the QA dispatch reading it. The freshness mechanism's first catch was the line denying the catcher existed.

This post is the current milestone's proof that the framework works *outside* its own repository: the first task delivered in a spoke, through the installed extension, end to end. The pull request that shipped it also carried this site's pointer file — so the repository you are reading from is now a CodeCrew spoke, and was enrolled by the protocol it was being enrolled into.

## Where it is

Early. Version 0.1, GitHub-only backend, one project using it in anger — and deliberately intentional about which GitHub platform features it depends on, so that adopters on a free plan are not quietly excluded. The [SPEC](https://github.com/radiusred/gh-codecrew/blob/main/SPEC.md), the role contracts, and the milestone documents — including the decisions and the failures above — are all in [the repository](https://github.com/radiusred/gh-codecrew). If the idea of a software crew whose discipline is enforced by refusal codes rather than good intentions appeals to you, the whole record is public: start with the SPEC, then read the milestone docs to watch the protocol harden itself.
