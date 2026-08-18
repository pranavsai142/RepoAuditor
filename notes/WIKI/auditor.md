# Headless Grok auditor

Deterministic metrics cannot tell “3 added lines, all comments” from a feature. After collect/flag, we hand each repo an **evidence pack** and run **Grok Build headless** (`grok --prompt-file`, documented in the Grok user guide as non-interactive `-p` / `--prompt-file` mode).

## Trigger

```bash
uv run repoauditor scan /path/to/department --out /tmp/ra --as-of 2024-07-01
uv run repoauditor analyze /tmp/ra --as-of 2024-07-01
```

Requires the `grok` CLI on PATH (or `GROK_BIN`). Auth: existing Grok login or `XAI_API_KEY`.

`scripts/verify.sh` does **not** call Grok (`--no-analyze`). Product `scan` always analyzes **once per repo** (mapper → investigator → scorer in that call). There is no department-wide executive Grok call. Each repo report carries its own `headline` + `executive_summary` on the repo detail page. The summary is written **last**, after every inspector tag is scored. It describes the tree and the record for a reader who has not seen the tags. Concerns and flags go in that story where they arise — not as a closing list of tag names. Ordinary readings (fork drift, student work, research iteration) stay available when the files support them. Not a second inspection and not a README restatement.

## Operating protocol (targeted investigation)

Same three stages on every repo. The prompt is a **catalog** (paths + counts). The pack and slim brief stay on disk. The tree is cwd. Context is ~200k — do not dump thousands of commits into the prompt.

1. **Mapper** (`explore`, read-only) — list HEAD, read README, sample real source. Inform: purpose, category, head_substance, readme_match.
2. **Investigator** (`explore`, read-only, fed the mapper notes) — follow flags and hunches. Do not stop at the README. Inform: commit_substance, wip, bots, padding, occupancy, AI.
3. **Scorer** (parent) — assign every scored tag +1 / 0 / −1. Cut through the veil.
4. **Summary** (parent, last) — headline + executive_summary from the scored tags, flags, and anomalies. JSON only.

Blocked: `write`, `search_replace` (do not edit the evidence). Web is off. Everything else stays, including `read_file`, `grep`, `list_dir`, `Agent`, and shell for `git show` of pack hashes. `--max-turns 512` (each parent tool call is a turn; `--timeout` default 86400s is only wall clock). The prompt lists file paths; Grok (or you) open them.

## Pack

On disk at `analysis/packs/<repo>.json`: rolled metrics, HEAD kinds, README excerpt, workflow/source samples, recent commits + patches + substance, flags, **all** allowed hashes, checklist.

`analysis/reports/<repo>.brief.json` is a smaller sample (capped hashes/paths/patches) for a first read.

`analysis/reports/<repo>.prompt.md` is only a catalog: paths + counts + flag names. It does not inline the pack.

## Checklist

purpose, category, head_substance, commit_substance, readme_match, wip_theater, bot_vs_human, padding, occupancy, ai_assistance, demo_vs_durable, run_the_business, requirements_theater, greenfield_vs_buy, next_inspect.

Dashboard sort key: see [scoring.md](scoring.md). Each scored tag is +1 / 0 / −1; the repo inspector score is their sum. `next_inspect` is not scored.

`run_the_business` is live critical work or a finished migration now in service — not “shared service.” `greenfield_vs_buy` is the half-baked custom stand-in for enterprise software that is normally bought. Both stay org- and vendor-agnostic.

## What not to do

- Do not let it edit the repo (`write` / `search_replace`).
- Do not invent commits (validator still strips unknown hashes).
- Do not treat inspector score as a verdict. It is a sort key. See [scoring.md](scoring.md).
