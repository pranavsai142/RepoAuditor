# SOUL_DRIVER — RepoAuditor

**What this project actually is, right now.**

RepoAuditor is an office-scale forensic audit tool for source-control activity. It takes a **collection of repositories** (a whole department, not one repo) and reconstructs **commits, contributors, assistance fingerprints, and substance** so a reviewer can see how time is actually spent — and who is carrying **run-the-business** work versus **glorified hackathon theater**.

The product is not a vanity dashboard. The class of situation it exists for: after a leadership vacuum, headcount surges; staff are overloaded; project management publishes timelines with nothing behind them; people are pointed at **greenfield demos** and **week-one requirements markdown** that were never going to run; a month later they hop to the next invented requirements. Meanwhile the department's actual job — **shared services at scale** (security, logging, identity, the suites you buy instead of rebuilding) — is what other bureaus depend on so they do not each invent a hole-filled replacement. You cannot greenfield that at enterprise scale. Replacing a commercial suite with a vibe-coded AWS sketch is how you burn cash.

The tool stays **vendor- and org-agnostic**. Those shapes are encoded as detectors and a checklist, not as a named employer.

## Current North Star

Ingest a collection of repos, reconstruct the commit/contributor record, and produce **ranked, pattern-aware views** of both **repos** and **people** that make departmental time-spend and suspicious activity shapes obvious.

Ranking axes that must always be available (entry points, not the product):

- last commit (staleness / abandonment)
- volume of change (lines added / deleted / churn — defined honestly, never as a single magical "lines" number)
- number of distinct human contributors

The real deliverable is **pattern detection + evidence packs** on three lenses:

1. **Repo lens** — husk, WIP treadmill, bot farm, padding, hot-potato, island, graveyard, low-substance, AI-dominated, demo-replacement, requirements-markdown theater, ops vs demo.
2. **People lens** — fade, hop across thin greenfields, **who is actually important** (durable/ops repos vs thin demo repos).
3. **Interpretation** — Grok reads the metrics **and** the code/workflows. Scripts cannot tell a working shared-service from a requirements markdown that was never going to run. That is the executive summary.

## Operating Philosophy

- **Deterministic collection is the foundation.** Extract → assimilate → rank → flag is reproducible and model-free. It is not the finished audit.
- **Grok investigates on a leash.** Deterministic metrics and flags are the brief. Headless Grok then runs a three-stage targeted investigation (mapper → investigator → scorer) with subagents and repo tools, so it can cut through the veil. It must not edit the tree. `--no-analyze` is harness-only.
- **Department is the unit of analysis.** A single-repo view is a drill-down, not the home screen.
- **Evidence over accusation.** Every flag must open the exact commits, diffs, authors, and dates that produced it. Metrics never "prove guilt"; they rank what a human must inspect.
- **Shapes, not scores.** The diagnostic power is in *patterns over time* (cadence, duplication, handoff gaps, bot/human mix, sudden stop), not a single health number that can be gamed.
- **Repos and people are dual first-class objects.** The same underlying commit stream answers "what is this repo?" and "what was this person doing?"
- **Git is not a timesheet.** Absence of commits is not proof of absence of work; presence of ritual commits is not proof of work. The tool must say both out loud and still make the *shape* of the record unmistakable.
- **Bots are first-class, not noise to hide.** Dependabot-style traffic, CI authors, and generated commits must be labeled, filterable, and able to stand as a finding ("this repo is entirely bot-operated").
- **Reproducible scans.** Same repo set + same time window + same rules = same findings. Persist the raw extracted record so rankings can be re-run without re-cloning the world.
- **Smallest verifiable slice.** Ingest → reconstruct → rank → flag one real pattern, with tests against fixture repos that exhibit that pattern.

## Core Invariants (do not casually break)

- A finding without a path back to commits is a bug.
- Author identity must survive email aliases / noreply / bot suffixes as an explicit resolution problem — never silently merge or silently split people.
- "Lines" is always decomposed (additions, deletions, net, churn, files touched). Never a single unlabelled count.
- Duplicate / near-duplicate commit contents are a first-class signal (padding, rebase theater, copy-forward).
- Temporal gaps and ownership rotation are first-class signals (two weeks of one person, silence, another person).
- Contributor disappearance is a first-class signal (daily activity March–June, then stop).
- README-only / docs-only / empty-after-init repos are first-class signals.
- Human review remains the last step. The app ranks and explains; it does not issue verdicts.
- LLM / headless Grok answers that cite commits not in the pack are stripped. Paths it actually opened may be cited. The model ranks and explains; it does not issue verdicts.

## Target pattern catalog (founding set)

These are the shapes the product must make obvious. Names may change; the shapes must not be lost.

| Pattern | What it looks like |
|---|---|
| README husk | Init + half-baked README, little or no real code change |
| Perpetual WIP | Constant activity that never leaves "WIP" / never ships a coherent increment |
| Bot-operated | Commits dominated by bots; little or no human authorship |
| Commit padding | One person, regular cadence (e.g. one commit/day), same or near-same contents |
| Hot-potato / serial occupancy | Person A for ~2 weeks, gap, person B, little continuity |
| Contributor fade | Regular (even daily) commits for a bounded window, then abrupt stop |
| One-person island | All meaningful change from a single human despite "team" framing |
| Burst then graveyard | Intense short occupancy, then long silence |
| Low substance | Commits that look like volume but add only comments, markdown, or empty churn |
| AI-dominated | Most commits carry a coding-assistant fingerprint |
| Demo replacement | Replace/modernize/platform claims; tree is a scaffolded demo |
| Requirements theater | Week-one requirements markdown, no product or ops code |
| Greenfield hop | One person, short occupancy on several thin new repos |

More patterns may be added; none of these may be dropped without rewriting this file.

## How This Document Is Used

- Every new session starts by reading this (via `/init`).
- Update only when the fundamental "why" or these invariants change.
- Stack, scan mechanics, and UI live in handoffs and `DEV_NOTES.md`, not here.

The project succeeds when an auditor can point the tool at a department's clones and, in one sitting, see which repos are run-the-business shared services, which are demo/requirements theater, who is actually carrying ops, who is hopping greenfields, which assistants are writing the record, and click any of those claims down to commits.
