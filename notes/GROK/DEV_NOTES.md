# DEV_NOTES — RepoAuditor (Narrative State of Play)

**Purpose**: Lightweight, living summary of where the project actually is right now. Kept short by omission. Rich history lives in dated handoffs.

The real work is driven by:
- This file (current narrative)
- `SOUL_DRIVER.md`
- The most recent handoffs in `notes/GROK/handoffs/`

## Current Big Picture

Deterministic collection is the foundation; Grok is required on the product `scan` for the executive summary and for reading code/workflows. `--no-analyze` is harness-only. Fixture catalog is **17** repos. Verify does not call Grok.

Formulation lives in `notes/WIKI/system.md`. Git argv/numstat contract in `notes/WIKI/git-oracle.md`. Analog map in `notes/WIKI/analogs.md`. Contract: `notes/GROK/PROSPECT_BRIEF-2026-08-16-e2e.md`.

## Hard-Won Lessons

### 1. Vanity metrics are the enemy
- Rankings are entry points. Patterns + evidence packs are the product.

### 2. Git is evidence of the record, not of labor
- Caveat is on every HTML report. Extra flags on a fixture (e.g. padding also looks like an island) are honest, not bugs.

### 3. Identity is a research problem
- v1 key is `(name, lower(email))`. Aliases emit suggestions only.

### 4. PEP 668
- `scripts/verify.sh` uses a project `.venv`. Bare `pip install` on macOS system Python fails.

### 5. Persist enough at extract
- `head_paths` and `tag_count` are stored so `rank`/`flag` never call `git`.

## How We Work

- Run `/init` at the start of every session.
- Run `/done` when finishing meaningful work.
- Gate: `scripts/verify.sh`
- `git` is the oracle. Do not add GitPython or a hosting API.

## Next Focus

- Optional: overlay file for bot allowlist / identity merges (still never silent).
- Optional: time-window filter at derive time (`--since` / `--until` on persisted raw).
- Do not start a SPA or remote org crawl.

---

*Update this file lightly at the end of significant sessions. Put the real detail in the handoff.*
