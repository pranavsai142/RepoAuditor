# RepoAuditor

Department-scale forensic scan of **local git repositories**. Point it at a folder that already contains the repos. It reconstructs the commit/contributor record, ranks repos and people, and flags activity *shapes* (README husks, bot-operated trees, daily duplicate commits, hot-potato occupancy, contributor fade, …) with a path back to exact commits.

Git is not a timesheet. Absence of commits is not proof of absence of work; ritual commits are not proof of work. RepoAuditor ranks and explains; it does not issue verdicts.

Output contains names and emails. Treat it as sensitive audit data. Do not publish a scan.

## Input

A directory of already-cloned git repos. No GitHub/GitLab API, no clone step.

```text
department/
  team-api/.git
  leftover-readme/.git
  nested/deep/old-thing/.git
```

## Run

```bash
python -m repoauditor scan /path/to/department --out /tmp/ra-scan --as-of 2024-07-01
```

Writes JSON under `raw/` and `derived/`, then **always** runs headless Grok: per-repo interpretation (opens source + workflows) plus a department **executive summary**. `--no-analyze` is only for the test harness.

```bash
python -m repoauditor scan /path/to/department --out /tmp/ra-scan --as-of 2024-07-01
# re-run interpretation on an existing scan:
python -m repoauditor analyze /tmp/ra-scan --as-of 2024-07-01
```

Needs the `grok` CLI (`GROK_BIN` to override). Verify uses `--no-analyze` and does not call Grok.

Other commands: `discover`, `extract`, `rank`, `flag`, `pack`, `analyze`.

## Verify

```bash
scripts/verify.sh
```

Rebuilds the fixture department (17 synthetic repos) and runs pytest. Does not invoke Grok.

## Docs

- `notes/WIKI/system.md` — end-to-end formulation
- `notes/WIKI/git-oracle.md` — first-party git extract contract
- `notes/WIKI/analogs.md` — GrimoireLab / CHAOSS / Code Maat map
- `notes/WIKI/auditor.md` — headless Grok auditor
- `notes/GROK/SOUL_DRIVER.md` — why this exists
