# RepoAuditor

Department-scale forensic scan of **local git repositories**. Point it at a folder that already contains the repos. It reconstructs the commit/contributor record, ranks repos and people, and flags activity *shapes* (README husks, bot-operated trees, daily duplicate commits, hot-potato occupancy, contributor fade, …) with a path back to exact commits.

Output contains names and emails. Treat it as sensitive audit data. Do not publish a scan.

## Input

A **git repo** (the folder has `.git`) — scan that repo only. Nested `.git` folders inside it are ignored.

A **folder of clones** (the folder itself is not a git repo) — discover each repo under it and stop at the first `.git`. No GitHub/GitLab API, no clone step.

```text
department/
  team-api/.git
  leftover-readme/.git
  nested/deep/old-thing/.git
```

## Install

Requires [uv](https://docs.astral.sh/uv/) and `git`. From the repo root:

```bash
uv sync --group dev
```

## Run

```bash
uv run repoauditor scan /path/to/department --out /tmp/ra-scan --as-of 2024-07-01
```

Forks: `--since YYYY-MM-DD` drops older commits at extract so upstream history never enters ranks, flags, or the inspector.

Writes JSON under `raw/` and `derived/`, then a multi-page HTML report at `<out>/report/index.html` (sortable repo and people tables, charts, per-repo and per-person pages). Product `scan` then runs headless Grok for the inspector checklist. `--no-analyze` is only for the test harness.

```bash
uv run repoauditor scan /path/to/department --out /tmp/ra-scan --as-of 2024-07-01
# re-run interpretation on an existing scan:
uv run repoauditor analyze /tmp/ra-scan --as-of 2024-07-01
```

Needs the `grok` CLI (`GROK_BIN` to override). Verify uses `--no-analyze` and does not call Grok.

Other commands: `discover`, `extract`, `rank`, `flag`, `pack`, `analyze`.

## Verify

```bash
scripts/verify.sh
```

`uv sync --frozen --group dev`, rebuilds the fixture department (17 synthetic repos), and runs pytest. Does not invoke Grok.

## Docs

- `notes/WIKI/system.md` — end-to-end formulation
- `notes/WIKI/git-oracle.md` — first-party git extract contract
- `notes/WIKI/analogs.md` — GrimoireLab / CHAOSS / Code Maat map
- `notes/WIKI/auditor.md` — headless Grok auditor
- `notes/GROK/SOUL_DRIVER.md` — why this exists
