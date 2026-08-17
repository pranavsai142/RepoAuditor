# 2026-08-16 — Session close

Built on: founding seed + e2e pipeline handoff. This session turned the seeded mission into a working v1 and then tightened the LLM layer.

## What happened

- Input locked: a local folder of already-cloned repos. No GitHub/GitLab crawl.
- Built the deterministic pipeline: discover → extract (`git` oracle) → assimilate → substance → rank → flag → packs → static HTML.
- Added the mission class (agnostic): office-scale hackathon theater vs run-the-business shared services. Encoded as `ai_dominated`, `demo_replacement`, `requirements_theater`, `greenfield_hop`, assistance inventory, `is_ops` / durable vs thin people ranking.
- LLM layer: product `scan` always analyzes. Grok is **not** an investigator. Same operating protocol every repo, `--max-turns 1`, tools disallowed. Pack already contains metrics, README, patches, source samples, workflow text. Grok only comprehends. Department executive summary is a second one-shot over the metric pack.
- `--no-analyze` is harness-only. Verify never calls Grok.
- Tree committed as `6fe8ac5` (`Initial commit`). Working tree clean at close.

## Verification

Last full suite: **23 passed** (`pytest tests/`, ~67s). Fixture department: **17** synthetic git repos. `healthy-team` and `shared-ops` stay silent on theater flags. Extra flags on a fixture (padding also island/graveyard) are honest.

## Decisions locked this session

- Deterministic collection is the foundation; it is not the finished audit.
- Grok interprets; it does not investigate (no tool loop, no recount).
- Identity v1 = `(name, lower(email))`; suggestions only.
- Person = author. Lines always decomposed. Bots and assistants labeled, never dropped.
- CLI + JSON + static HTML. No SPA, no hosting API, no GitPython.

## Hard lessons

- Extra flags on a fixture are not bugs if the record supports them.
- `low_substance` must not punish ops repos (runbooks/security markdown are not theater).
- macOS system Python is PEP 668; `scripts/verify.sh` uses `.venv`.
- Preload file excerpts into the pack or the model will wander and cost turns.

## Current state

Product path: `python -m repoauditor scan DIR --out OUT --as-of YYYY-MM-DD`  
Harness: `scripts/verify.sh`  
Docs: `notes/WIKI/system.md`, `git-oracle.md`, `analogs.md`, `auditor.md` (protocol).

## Honest opens

- No live Grok run against a real department folder was done in this session (only mocked analyze).
- No `--since`/`--until` at derive time.
- No operator overlay for bots/identity merges.
- No merge-commit or binary fixture (parser rules exist).
- Fade/graveyard/hop thresholds are v1 constants.
- Initial commit message is generic; history is one commit.

## Next session should start on

1. `/init`.
2. Point `scan` at a real folder of department clones (start with `--no-analyze` if you only want the metric pack; product path includes Grok).
3. Do **not** start a SPA or org crawl.
4. Optional follow-ons: derive-time window, identity overlay, live executive-summary sanity check on real packs.
