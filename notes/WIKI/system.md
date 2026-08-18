# End-to-end system (v1)

Input is a **directory that already contains the department’s git repos**. The operator cloned or copied them. We do not talk to GitHub or GitLab.

```
input dir
    │
    ▼
 discover   stop at first .git, depth ≤ 8
    │
    ▼
 extract    git log --all --numstat  →  raw/commits.jsonl
    │
    ▼
 assimilate identities + bot labels + repo/person rolls
    │
    ├──► substance   git show → comment / docs / code line mix
    ├──► rank        last commit / churn / human contributors
    ├──► flag        founding patterns + low_substance + evidence hashes
    ├──► pack        per-repo brief for the auditor agent
    ├──► analyze     one headless Grok call per repo (mapper → investigator → scorer + repo executive)
    ▼
 report     JSON + static HTML  (ranks, explains, no verdicts)
```

This is GrimoireLab’s collect → enrich → identity → display, collapsed onto one laptop and one oracle (`git`).

## 1. Input / discovery

- If the path you pointed at **is a git repo** → scan that repo only. Nested `.git` folders inside it are ignored.
- If the path is **not** a git repo → treat it as a folder of clones. Walk, stop at the first `.git` of each child, depth ≤ 8.
- Skip: `.git`, `node_modules`, `.venv`, `venv`, `__pycache__`.
- `repo_id` = directory name when the input is the repo; otherwise POSIX path relative to the input root.

## 2. Collection (metrics from git)

One fact row per `(repo_id, commit hash)`:

`hash, tree, parents, is_merge, author_name, author_email, author_date, committer_*, subject, files[], additions, deletions, net, churn, files_changed, patch_id, is_bot (later)`

Line counts come only from `--numstat` and stay **decomposed**. Binaries stay `null`, not `0`. Merge numstat is stored on the row but **excluded** from volume sums.

Extract also persists `head_paths` and `tag_count` so later stages never call `git`.

Raw output is the durable fact table. `rank` / `flag` re-run from it.

## 3. Consolidation / assimilation

**Identities.** v1 key = `(author_name, lower(author_email))`. Same name + two emails = two people. Same email + two names = two people. Suggestions (same-email, same-name, noreply local-part) are written to `identity_suggestions.json` and **never auto-applied**.

**Bots.** Labeled (`is_bot`, `bot_reasons`). Default allowlist + `[bot]` / `\bbot\b`. Bots stay in the raw table. Human counts exclude them. A repo that is only bots is a finding, not an omit.

**Repo roll-up.** last author date, commit_count, human_contributor_count, bot_contributor_count, additions, deletions, net, churn, files_changed (non-merge, non-binary for volume), head_paths, tag_count.

**Person roll-up (department-wide).** first/last author date, distinct UTC days, repos touched, decomposed volume, commit hashes.

**Rankings (entry points, not the product).**

| Lens | Axes |
|---|---|
| Repos | last commit (oldest first), churn (highest first), distinct humans (lowest first) |
| People | last commit (oldest first), churn (highest first), repo count (highest first) |

There is no field named `lines`.

## 4. Pattern flags (founding catalog)

Thresholds live in `repoauditor/patterns/thresholds.py`. A finding without `evidence.commit_hashes` is a bug.

| Pattern | Lens | Shape |
|---|---|---|
| `readme_husk` | repo | ≤3 commits, HEAD tree is empty or docs/meta only |
| `perpetual_wip` | repo | ≥8 commits, ≥50% subjects match `\bWIP\b`, no tags |
| `bot_operated` | repo | ≥3 commits, human share < 15% |
| `commit_padding` | repo | one human, daily cadence, same tree or patch-id cluster |
| `hot_potato` | repo | human A streak, ≥7-day gap, different human B streak |
| `contributor_fade` | person | regular daily activity, then ≥30 days silent before `--as-of` |
| `one_person_island` | repo | exactly one human with real work, ≥5 human commits |
| `burst_graveyard` | repo | ≥8 commits in 14 days, then ≥45 days silent before `--as-of` |
| `low_substance` | repo | ≥3 sampled commits, ≥70% add no code lines (comments/docs/empty) |
| `ai_dominated` | repo | ≥4 commits, ≥50% have assistant trailers/authors/subjects |
| `demo_replacement` | repo | replace/modernize claims + scaffold markers (Vite/CRA-shaped) |
| `requirements_theater` | repo | requirements/spec markdown only, no product/ops code |
| `greenfield_hop` | person | ≥3 thin repos, each occupancy ≤21 days |

Copy on findings **explains**. It does not say guilty, malfeasance, or fired.

## 5. Display

```
uv run repoauditor scan <dir> --out <scan> --as-of YYYY-MM-DD
```

```
<scan>/raw/repos.json
<scan>/raw/commits.jsonl
<scan>/raw/extract_meta.json
<scan>/derived/identities.json
<scan>/derived/identity_suggestions.json
<scan>/derived/repos.json
<scan>/derived/people.json
<scan>/derived/rankings.json
<scan>/derived/findings.json
<scan>/derived/substance.json
<scan>/analysis/packs/*.json
<scan>/analysis/reports/*.json
<scan>/report/index.html
```

`scan --analyze` (or `repoauditor analyze <scan>`) runs **headless Grok**:

```text
grok --prompt-file <brief prompt> --json-schema <auditor schema> --output-format json \
  --system-prompt-override <mapper→investigator→scorer> --cwd <that repo> \
  --disallowed-tools search_replace,write --max-turns 512 --yolo --verbatim
```

The analyze prompt is a catalog (file paths + counts). Grok reads the pack/brief files, then explores the repo with subagents. It must still cite hashes from the pack. Invented hashes are stripped. Do not inline thousands of commits into the prompt (~200k context).

Verify does **not** call Grok. Analyze is optional and needs the `grok` CLI (or `GROK_BIN`).

HTML: dashboard at `report/index.html` (counts, week/month bars, sortable repo and people tables, inspector scorecards), plus `report/repos/` and `report/people/` drill-downs with day calendars. Sorting is a small local script, not a SPA. No verdict chrome.

Output contains names and emails. It is sensitive audit data, not for publication.

## 6. Verification

`scripts/verify.sh` rebuilds `tests/fixtures/department/` (11 synthetic git repos that embody the catalog + healthy/alias/nested controls) and runs pytest against `--as-of 2024-07-01`.
