# 2026-08-16 — Founding seed

## What happened

`/seed` was run on an empty `RepoAuditor` working tree. The portable memory system is now in place. No application code was written. The user's founding brief is the only source material: a department-scale auditor for git activity, aimed at seeing how a whole department spends time and at surfacing malfeasance-shaped patterns quickly.

## Founding brief (as given)

An app that takes a **collection of repositories**, systematically scans **commits and contributors**, and puts the information together for **audit**. Purpose: figure out exactly how a whole department is spending its time.

Rank things by:

- last commit
- number of lines
- number of contributors

Mission shapes called out explicitly:

- repos that are just a half-baked README
- things that are constantly in WIP
- things totally run by bots
- one person doing a duplicative change — one commit each day with the same contents
- a project that has one person for two weeks, then no action, then another person
- people analysis: this person was committing every day from March to June, then just stopped

Those metrics are meant to get to the bottom of malfeasance quickly.

## What was created

```
notes/GROK/
  SOUL_DRIVER.md          (synthesized from the brief)
  DEV_NOTES.md            (greenfield state)
  README.md               (canonical copy)
  handoffs/
    README.md             (canonical copy)
    ARCHIVE/README.md     (canonical copy)
    2026-08-16-founding-seed-handoff.md   (this file)
notes/WIKI/INDEX.md       (canonical starter)
```

Skills already present (not re-copied): `.grok/skills/seed/`, `init/`, `done/`.

## Decisions locked in the soul (not in code)

- Department (a collection) is the unit of analysis; a single repo is a drill-down.
- Dual first-class lenses: **repos** and **people**.
- Rankings are entry points. Patterns + evidence packs are the product.
- Every flag must drill to raw commits. No verdicts from the app.
- Bots are labeled and filterable, not hidden.
- "Lines" is always additions / deletions / net / churn / files — never one unlabeled number.
- Git is not a timesheet; the caveat stays visible.
- Founding pattern catalog is listed in `SOUL_DRIVER.md` and must not be silently dropped.

No tech stack, hosting, or git-host API was chosen. That is intentional.

## Current state of the tree

Empty product. Memory only. Ready for `/init` and then a first slice conversation (or `/prospect` / `/research` / `/design` once the input surface is clearer).

## Open questions for the next session

These are the things that must be decided or researched before implementation sprawls:

1. **Where do the repos come from?** Explicit URL/path list, GitHub org, GitLab group, local clone directory, or all of the above?
2. **Auth and privacy.** PAT / app install / SSH? How is a department's private code handled? Scan results will contain people names and emails — treat as sensitive audit data.
3. **Identity.** How aggressive should author clustering be (same email, same name, noreply mapping, org directory)?
4. **Bot definition.** Allowlist of known bot authors vs heuristics vs both?
5. **Time window.** Default scan range (all history vs last N months)? Timezone for "every day"?
6. **Duplicate contents.** Exact tree hash, patch hash, or fuzzy (whitespace / generated files)?
7. **WIP signal.** Commit-message tokens, branch names, lack of tags/releases, open PR age — which is in v1?
8. **Product shape.** CLI that emits a report, local web app, or both? First slice should probably be a reproducible scan + report against fixtures, not a UI.
9. **Legal/HR framing.** The tool ranks evidence for a human auditor. Copy and UX must not present scores as proof of misconduct.

## What the next session should start on

1. Run `/init`.
2. Do **not** scaffold a web app yet.
3. Either `/prospect` the ingest + fact-table + fixture strategy, or lock the four "Next Focus" items in `DEV_NOTES.md` in conversation and then design the smallest slice: **N fixture repos that embody founding patterns → extract commit/contributor record → rank → flag one pattern with drill-back.**

The first honest increment is a detector that finds "one commit a day, same contents" (or "README husk") on a fixture — not a dashboard.
