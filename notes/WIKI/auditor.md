# Headless Grok auditor

Deterministic metrics cannot tell “3 added lines, all comments” from a feature. After collect/flag, we hand each repo an **evidence pack** and run **Grok Build headless** (`grok --prompt-file`, documented in the Grok user guide as non-interactive `-p` / `--prompt-file` mode).

## Trigger

```bash
python -m repoauditor scan /path/to/department --out /tmp/ra --as-of 2024-07-01
python -m repoauditor analyze /tmp/ra --as-of 2024-07-01
```

Requires the `grok` CLI on PATH (or `GROK_BIN`). Auth: existing Grok login or `XAI_API_KEY`.

`scripts/verify.sh` does **not** call Grok (`--no-analyze`). Product `scan` always analyzes: one shot per repo + one department executive summary.

## Operating protocol (feels deterministic)

Same steps on every repo. The pack is the entire world.

- P0. No tools. No search. No recount.
- P1. Metrics, findings, substance, file excerpts are given facts.
- P2. Compare README to tree / source_samples / workflow_files (already in the pack).
- P3. Answer every checklist id in order. Short. Or `cannot tell from pack`.
- P4. See through the veil: volume ≠ work; comments ≠ product; scaffold ≠ replacement suite.
- P5. JSON only. No investigation narrative.

The questions are identical. The tree is not. That is the only place the model is allowed to think.

Scripts pre-load README, up to 3 source files, and workflow file text so Grok never has to `read_file`. Headless run is `--max-turns 1` with tools disallowed.

## Pack

Rolled metrics, HEAD kinds, README, workflow file text, source samples, recent commits + patches + substance, flags, allowed hashes, checklist.

## Checklist

purpose, category, head_substance, commit_substance, readme_match, wip_theater, bot_vs_human, padding, occupancy, ai_assistance, demo_vs_durable, run_the_business, requirements_theater, greenfield_vs_buy, next_inspect.

## What not to do

- Do not let the model wander the repo (no tool loop).
- Do not let it invent commits (validator strips unknown hashes).
- Do not treat its category as a score.
