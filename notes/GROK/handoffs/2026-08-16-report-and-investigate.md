# 2026-08-16 — Report overhaul + targeted investigate

Built on: session-close + e2e pipeline. This session took v1 to a real-repo report and flipped Grok from one-shot clerk to targeted investigation.

## What happened

- Discover: point at a git repo → scan that repo only. Nested `.git` (e.g. `thesis/`) ignored. Point at a folder that is not a repo → walk children.
- `uv` is the install/run path (`uv.lock`, `scripts/verify.sh`).
- Extract: non-UTF-8 `git show --patch` no longer aborts; patch-id is raw bytes. Inherited `GIT_DIR` cleared.
- Report is a multi-page static site: dashboard + repo pages + person pages. Sortable tables, default columns + checkbox extras, drag-to-reorder, compact numbers (626K / 1.27M). No `shape` column. No timesheet banner.
- Repo people table: first/last commit **in that repo**. Flags carry who/when/gap, not just hashes. Branches shown. No PRs (no hosting API).
- Inspector score: 14 tags, +1 / 0 / −1, sum is a sort key. Rubric in `notes/WIKI/scoring.md`. Green/yellow/gray strip on the dashboard.
- Analyze: pack stays on disk. Parent Grok runs mapper → investigator → scorer with subagents. Only `write` / `search_replace` blocked. `--max-turns 16`. Exec summary still one-shot. Headless prompts kept lean (pack path + loop; no restated checklist/rubric).
- Parser: walk JSON objects, pick the report-shaped one. Fresh `--session-id` per analyze. Analyze failure no longer kills `scan`. Stdout stashed next to the prompt on parse fail.

## Quirk — do not resume a live headless session

Analyze uses `--cwd <scanned repo>`. Grok stores the session under that path.

- **While scan/analyze is still running:** do not attach a TUI to that session (`grok --resume` / `/resume` in that cwd). Two writers. Stdout can become extra JSON.
- **After the process exits:** safe. `cd <scanned repo> && grok --resume`. Finished session only. Subagent children live under the same tree.

Do not put this quirk in auditor/Grok prompts or `auditor.md` (token waste). It belongs here and in DEV_NOTES.

TUI-side still wanted: refuse resume of a session with a live headless client.

## Verification

Last full `scripts/verify.sh`: **33 passed** (plus later auditor parse tests). Verify never calls Grok.

## Decisions locked

- Local clones only. `uv run repoauditor`.
- Point-at-repo vs folder-of-repos as above.
- Grok investigates on a leash (3 stages, no repo edits). Prompts stay metaskill-lean.
- Inspector score is a sort key, not a verdict.
- Resume headless only after the process exits.

## Current state

Product: `uv run repoauditor scan DIR --out OUT`  
Report: `<out>/report/index.html`  
Working tree is dirty (not committed).

## Honest opens

- TUI still allows resume of a live headless session.
- No `--since`/`--until` at derive time.
- No operator identity/bot overlay.
- Analyze does not print sessionId (find via that repo’s `/resume` after exit).
- 500-repo exec pack could get large (people rolls).

## Next session

1. `/init`.
2. Do not start a SPA or org crawl.
3. Optional: print sessionId after analyze; TUI lock on live sessions; derive-time window.
