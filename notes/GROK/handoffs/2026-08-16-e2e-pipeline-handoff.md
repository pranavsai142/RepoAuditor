# 2026-08-16 — End-to-end pipeline (fieldgoal + fabel-open-ended)

Built on: founding seed handoff + `/fieldgoal` + `/fabel-open-ended`. Input lock from the user: **a directory that already contains the repos**.

## Verification status

`scripts/verify.sh` — **13 passed** (pytest, ~24s after fixture build).

Manual: `python -m repoauditor scan tests/fixtures/department --out /tmp/ra-scan --as-of 2024-07-01` → 11 repos, 182 commits, 16 findings. All eight founding patterns fire on the intended fixtures. `healthy-team` is silent. Identity aliases stay two people + suggestions.

## Analog map (fabel index)

No analog captures existed in-tree. First-party sources:

- **Git** is the oracle (`git log --all --numstat`, pretty-formats `%H %T %P %an %ae %aI …`, binaries as `- -`).
- **GrimoireLab**: collect → enrich → identity → display. We collapsed that onto one laptop. We refused SortingHat auto-merge and the ELK/Kibana stack.
- **Code Maat**: git produces a log; analyses consume it; volume is added/deleted. We persist richer JSON.
- **CHAOSS**: Contributors (commit authors only), Inactive Contributors → fade, Bot Activity → label not drop, Contributor Absence Factor → explanation for one-person island.

## What was delivered

Formulation:

- `notes/WIKI/system.md` — full pipeline
- `notes/WIKI/git-oracle.md` — locked argv and numstat rules
- `notes/WIKI/analogs.md` — port/refuse
- `notes/GROK/PROSPECT_BRIEF-2026-08-16-e2e.md` — Just-Go contract

Product (Python 3.11+, stdlib + subprocess `git`, pytest in `.venv`):

- `discover` — recursive, stop at first `.git`, depth 8
- `extract` — fact table + `head_paths` + `tag_count` + `patch_id`
- `assimilate` — identity pair key, bot labels, repo/people rolls
- `rank` — last commit / churn / human contributors (no `lines` field)
- `flag` — eight founding patterns, each with commit hashes
- `scan` — JSON tree + static HTML with the locked timesheet caveat

Harness: `tests/fixtures/build_fixtures.py` builds 11 real git repos.

## Bugs / extras noticed (honest, not hidden)

A fixture can trip more than one pattern. Example: `commit-padding` is also a one-person island and, as of 2024-07-01, a burst-then-graveyard. That is the record. Tests require the *intended* flag and require `healthy-team` to have none.

`scripts/verify.sh` creates `.venv` because macOS system Python is PEP 668-managed.

## Decisions locked

- Input = local directory only.
- `git log --all`; person = author; identity = `(name, lower(email))`; suggestions only.
- Bots labeled, never dropped.
- UTC date of `%aI`; tests pin `--as-of 2024-07-01`.
- Display = CLI + JSON + static HTML. No SPA.

## Honest opens

- No `--since`/`--until` at derive time yet (extract is all history).
- No operator overlay for bot list or identity merges.
- No binary-file fixture (parser implements the `- -` rule; oracle test would catch a regression if a binary appeared).
- No merge-commit fixture (merge numstat is excluded in code; untested on a real merge).
- Fade/graveyard windows are v1 constants, not researched “correct” HR thresholds.

## Next session

Do not scaffold a web app or GitHub crawl. If continuing: derive-time time window, merge + binary fixtures, or an explicit identity-overlay file.

## Bottom line

An auditor can point `repoauditor scan` at a folder of clones and get ranked repos/people plus drillable flags. One venv + `scripts/verify.sh` stands between a clean tree and a green matrix.
