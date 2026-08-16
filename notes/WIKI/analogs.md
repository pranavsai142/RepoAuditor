# Analog map — what to port, what to refuse

There were **no** analog captures in this repo at seed. These are first-party / analog systems, not vendors to copy.

## GrimoireLab (CHAOSS) — pipeline shape

Source: https://chaoss.github.io/grimoirelab/

GrimoireLab is three stages:

1. **Gather** — Perceval (git backend runs `git`; can also ingest a prebuilt `git log`)
2. **Enrich** — GrimoireELK; SortingHat **merges** identities and affiliations
3. **Consume** — Sigils/Kibana dashboards, Manuscripts reports

Perceval recommended log (do not vendor Perceval):

```text
git log --raw --numstat --pretty=fuller --decorate=full --parents --reverse --topo-order -M -C -c --remotes=origin --all
```

**Port:** the stage split (collect → enrich → identity → display). Persist raw so derive can re-run without `git`.

**Refuse:** Elasticsearch/Kibana stack. SortingHat **auto-merge** of identities (soul: never silently merge). Multi-source (issues, chat, GitHub API) — v1 is local git only.

## Code Maat — forensic VCS mining

Source: https://github.com/adamtornhill/code-maat

Preferred git2 log:

```text
git log --all --numstat --date=short --pretty=format:'--%h--%ad--%aN' --no-renames
```

Analyses we echo, not copy: `summary`, `authors`, `abs-churn`, `author-churn`, `entity-ownership`, `age`. Code Maat itself has **no visualisations** (CSV out).

**Port:** `git` produces the log; analyses consume the log; volume is **added + deleted**, never one “lines” number; author is the person (`%aN` analog — we store raw `%an` instead of mailmap).

**Refuse:** their log file as our persistence format (we keep richer JSON). `--date=short` (we need `%aI` + UTC). Mailmap `%aN`. Coupling / architectural grouping (out of v1 scope).

## CHAOSS metrics — named questions, not scores

| Metric | URL | How we use it |
|---|---|---|
| Contributors | https://www.chaoss.community/kb/metric-contributors/ | People lens. v1 = **commit authors only** (must say so). Visual analogs: list, count, activity over time, first-commit date. |
| Inactive Contributors | https://www.chaoss.community/kb/metric-inactive-contributors/ | Fade: last contribution + inactivity interval before `--as-of`. |
| Bot Activity | https://www.chaoss.community/kb/metric-bot-activity/ | Label + keep. Ratio of bot/human. Never drop bots. |
| Contributor Absence Factor (ex bus factor) | https://www.chaoss.community/kb/metric-contributor-absence-factor/ | Smallest set making 50% of commits. **Explanation text** for one-person island, not a guilt score. |
| Elephant Factor | https://www.chaoss.community/kb/metric-elephant-factor/ | Company-level analog. Out of v1 (no org directory). |

CHAOSS pages all carry a **data-ethics** warning (names/emails are sensitive). Our report footer must say the scan is not for publication.

## Display analogs

- GrimoireLab Sigils / Manuscripts: department dashboard + generated report
- Code Maat: miner emits tables; someone else visualises

**Our v1:** CLI + JSON evidence pack + **static HTML**. No SPA, no server.

## Planned vs current (at formulation)

| Index element | Analog | v1 |
|---|---|---|
| Input | Perceval URL / git-log file | **Directory of local repos** (locked) |
| Collect | Perceval git / Code Maat log | `discover` + `extract` via locked argv |
| Identity | SortingHat merge | Pair key + **suggestions only** |
| Bots | CHAOSS Bot Activity | Heuristics + allowlist, never drop |
| Rank | Code Maat authors / age / churn | last commit, decomposed volume, human count |
| Patterns | (none of the analogs are forensic-malfeasance tools) | Eight founding shapes in SOUL_DRIVER |
| Display | Sigils / Manuscripts / CSV | JSON + static HTML + timesheet caveat |
