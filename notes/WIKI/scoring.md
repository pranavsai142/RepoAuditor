# Inspector scoring rubric

Used to **sort** a department dashboard (hundreds of repos). It is a ranking aid, not a verdict.

Each scored checklist tag is:

| Answer | Score |
|---|---|
| ok (no concern, real answer) | **+1** |
| cannot tell / missing after analyze | **0** |
| concern | **−1** |

**Inspector score** for a repo = sum of the 14 scored tags. Range **−14 … +14**. Lower = more inspector concern. Unanalyzed repos have no score and sort after analyzed ones.

`next_inspect` is **not** scored. It only names commits to open first.

## Tags (what +1 is looking for)

| Tag | Looking for (+1) | −1 looks like |
|---|---|---|
| `purpose` | identifiable purpose | cannot tell what the tree is for |
| `category` | known kind of repo (service, library, infra, …) | husk / unknown with concern |
| `head_substance` | real code at HEAD that could run or be imported | docs/comments/config/placeholders only |
| `commit_substance` | recent commits change behavior | comments, markdown, whitespace, lockfile, empty |
| `readme_match` | README describes the actual tree | over-claim |
| `wip_theater` | ships coherent increments | perpetual WIP, no increment |
| `bot_vs_human` | humans do the meaningful work | bots dominate |
| `padding` | not attendance commits | ritual / duplicate / comment-only cadence |
| `occupancy` | stable occupancy | fade, hot-potato, burst-then-graveyard, island |
| `ai_assistance` | human-directed assistance | autonomous assistant commit streams |
| `demo_vs_durable` | durable system that still runs | scaffolded demo / unfinished rewrite pitch |
| `run_the_business` | live critical work, or a migration that finished and is in service | side / unfinished tree; `is_ops` is a path heuristic only |
| `requirements_theater` | more than a spec document | requirements markdown only |
| `greenfield_vs_buy` | real suite kept, or a replacement that actually landed | half-baked custom stand-in for enterprise software already in use |
| `next_inspect` | *(unscored)* hashes a human should open first | — |

The dashboard **score** column is that sum (default sort, lowest first). Tag columns use the same names as the scorecard boxes (`purpose`, `head substance`, …). Enable a tag column to sort the department on that question alone.

Deterministic flags (`hot_potato`, `commit_padding`, …) are a separate column. They are not in this sum.

## How to use it at 500 repos

1. Run product `scan` (analyze on).
2. Open `report/index.html`.
3. Repos are ordered by inspector score, worst first.
4. Turn on a tag column (Columns checkboxes) and click its header to sort by that tag only.
5. Open a repo for the written checklist answers.
