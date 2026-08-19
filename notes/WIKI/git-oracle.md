# Git oracle — extract contract

`git` on PATH is the only source of commit facts. No hosting API. No GitPython. The parser must match these first-party rules.

## Locked argv

```text
git -C <repo> -c i18n.logOutputEncoding=UTF-8 log --all --no-mailmap --date=iso-strict --numstat \
  --format=format:'%x1e%H%x00%T%x00%P%x00%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI%x00%s'
```

Records split on `\x1e`. Fields split on `\x00`. Following lines until the next `\x1e` are `--numstat` rows: `adds\tdels\tpath`.

## Placeholders (pretty-formats)

Cited from https://git-scm.com/docs/pretty-formats

| Token | Meaning |
|---|---|
| `%H` | commit hash |
| `%T` | tree hash |
| `%P` | parent hashes (space-separated) |
| `%an` `%ae` `%aI` | author name, email, **strict ISO-8601** date |
| `%cn` `%ce` `%cI` | committer name, email, strict ISO-8601 date |
| `%s` | subject (first line only) |

Do **not** use mailmap forms `%aN` / `%aE`. Identity v1 is the raw pair. `--no-mailmap` is required.

Author vs committer: both stored. Rankings, cadence, fade, occupancy use **author** + **author date**.

## `--numstat` (git-log / git-diff)

Cited from https://git-scm.com/docs/git-log (`--numstat`):

> Similar to `--stat`, but shows number of added and deleted lines in decimal notation and pathname without abbreviation, to make it more machine friendly. For binary files, outputs two `-` instead of saying `0 0`.

If `adds == '-'` or `dels == '-'`: `is_binary=true`, `additions=null`, `deletions=null`. Never coerce binaries to 0.

- `net = additions - deletions` only when both are ints
- `churn = additions + deletions` only when both are ints
- `files_changed` counts every path, including binaries

Merge commits: keep the row (`is_merge` if `len(parents) > 1`). **Do not** add merge `--numstat` into repo/person volume sums (merges double-count). Still increment `commit_count`.

## `--all`

Cited from https://git-scm.com/docs/git-log:

> Pretend as if all the refs in `refs/`, along with `HEAD`, are listed on the command line.

Dedup by full hash. Do not use `--first-parent` for discovery.

Default with no revision range is `HEAD` only — that is why `--all` is locked. Hot-potato work that lives on a side branch must still appear.

## Dates

`--date=iso-strict` / `%aI`: strict ISO-8601 with offset (https://git-scm.com/docs/git-log `--date`).

“Every day” = **UTC calendar date** of `%aI`. Persist the raw string.

`--as-of YYYY-MM-DD` is UTC midnight. Fixture tests always pass `--as-of 2024-07-01`. Never use the machine’s “today” in tests.

`--since YYYY-MM-DD` (optional) is appended as `git log --since=` and commits whose **author** UTC date is still earlier are dropped. Persist `since` in `extract_meta.json`.

## Duplicate contents

- `tree` = `%T` (https://git-scm.com/docs/pretty-formats)
- `patch_id` = `git patch-id --stable` on the **raw bytes** of `git show --format= --patch <commit>` (https://git-scm.com/docs/git-patch-id). Never decode the patch as UTF-8. Null for merges and empty patches.

“Same contents” = equal `tree` **or** equal `patch_id`. No fuzzy matching in v1.

## HEAD tree and tags (persisted at extract)

So `rank` / `flag` never call `git`:

- `git ls-tree -r --name-only HEAD` → `head_paths`
- `git for-each-ref refs/tags` count → `tag_count`

## What this is not

Git is not a timesheet. The extract is the **record**. Absence of commits is not proof of absence of work; ritual commits are not proof of work.
