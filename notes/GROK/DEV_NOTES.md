# DEV_NOTES — RepoAuditor (Narrative State of Play)

**Purpose**: Lightweight, living summary of where the project actually is right now. Kept short by omission. Rich history lives in dated handoffs.

The real work is driven by:
- This file (current narrative)
- `SOUL_DRIVER.md`
- The most recent handoffs in `notes/GROK/handoffs/`

## Current Big Picture

v1 plus the report + investigate layer. Deterministic scan is the foundation; product `scan` then runs targeted Grok investigation (mapper → investigator → scorer → summary). `--no-analyze` is harness-only. Report is a sortable multi-page HTML site. Inspector score rubric: `notes/WIKI/scoring.md`.

Formulation lives in `notes/WIKI/system.md`. Git argv/numstat contract in `notes/WIKI/git-oracle.md`. Analog map in `notes/WIKI/analogs.md`. Contract: `notes/GROK/PROSPECT_BRIEF-2026-08-16-e2e.md`.

## Hard-Won Lessons

### 1. Vanity metrics are the enemy
- Rankings are entry points. Patterns + evidence packs are the product.

### 2. Extra flags on a fixture are honest
- Padding also looking like an island is the record, not a bug. The HTML report no longer carries the timesheet disclaimer.

### 3. Identity is a research problem
- v1 key is `(name, lower(email))`. Aliases emit suggestions only.

### 4. Use uv, not system pip
- `scripts/verify.sh` uses `uv sync` / `uv run`. Bare `pip install` on macOS system Python fails (PEP 668).

### 5. Persist enough at extract
- `head_paths` and `tag_count` are stored so `rank`/`flag` never call `git`.
- `git show --patch` is file bytes, not UTF-8. A latin-1 or binary-as-text blob must not abort extract.

### 6. Targeted investigation, not a free wander
- Pack and slim brief stay on disk. The prompt is a catalog (paths + counts), not 4k commits. Subagents read what a tag needs (~200k context). Only `write` / `search_replace` are blocked.

### 7. Resume headless only after it exits
- Analyze sessions live under the **scanned repo** cwd. After the process exits: `cd` there, `grok --resume`. Do not attach while scan is still running.

## How We Work

- Run `/init` at the start of every session.
- Run `/done` when finishing meaningful work.
- Gate: `scripts/verify.sh`
- `git` is the oracle. Do not add GitPython or a hosting API.
- Point at a repo → scan that repo. Point at a folder of clones → discover children. Report is a sortable multi-page HTML site.

## Next Focus

Live analyze on real clones. Optional: print sessionId, TUI lock on live headless sessions, `--since`/`--until`. No SPA, no remote crawl.

---

*Update this file lightly at the end of significant sessions. Put the real detail in the handoff.*
