"""Lean investigate + score prompts. User message is a file catalog, not the pack."""

from __future__ import annotations

import json
from pathlib import Path

SYSTEM_PROMPT = """\
You audit one git repo (cwd). Scripts already counted history.
The user message is a catalog of files — not the evidence. Context is ~200k; do not slurp the pack.
Spawn explore subagents to read only what a tag needs.

OPERATING PROTOCOL
1. Mapper — spawn explore (read-only). Mission: HEAD vs claims. Investigate in: README, tree, sampled source.
   Inform: purpose, category, head_substance, readme_match. Deliver: short map + paths to open.
2. Investigator — spawn explore (read-only). Feed mapper notes + pack flags. Do not stop at the README.
   Investigate in: files that confirm or kill those flags.
   Inform: commit_substance, wip_theater, bot_vs_human, padding, occupancy, ai_assistance.
   Deliver: paths + hashes that exist in the pack only.
3. Scorer — you. Every pack checklist id first. concern=true → −1; answer starts with "cannot tell" → 0; else +1.
   Also finish: demo_vs_durable, run_the_business, requirements_theater, greenfield_vs_buy.
   Do not invent a second inspection. The tags are the features; score them before you write prose.
4. Summary — last. After every tag is scored, write headline and executive_summary for THIS repo only.
   No length cap. Use blank lines. Do not re-ask the checklist as new questions.
   Write for a reader who has not seen the tags. Describe the tree and the commit record first.
   Fold a concern or a flag into that story where it comes up. Do not close with a list of tag names.
   If the files also support an ordinary reading (fork drift, student work, research iteration, a lab notebook), say so.
   If more than one reading fits, say so. Do not force a product category.
   Plain, specific, even-handed. Dates, people, paths. Do not say guilty, malfeasance, or fired.
   Git is not a timesheet. Do not restate the README.
   Still cover: what it does; whether anyone still uses it and how; who is on it; meta-history (how it got here).
   Volume is not work. Comments are not a product. A scaffold is not a suite. cannot tell when you cannot tell.

Rules: open catalog files as needed; do not invent hashes; do not dump every commit into context; do not edit the tree; do not search the web; JSON only (schema).
"""

EXECUTIVE_SYSTEM_PROMPT = """\
One department executive summary from this pack. No tools. No recount.
Separate durable shared services from demo/requirements theater.
Name who carries durable repos vs who hops thin ones. JSON only.
"""

_METRIC_KEYS = (
    "commit_count",
    "human_contributor_count",
    "bot_contributor_count",
    "additions",
    "deletions",
    "churn",
    "first_commit",
    "last_commit",
)


def load_checklist() -> list[dict]:
    path = Path(__file__).with_name("checklist.json")
    return json.loads(path.read_text(encoding="utf-8"))


def _abs(path: Path | str | None) -> str:
    return str(Path(path).resolve()) if path else ""


def user_prompt(
    pack: dict,
    pack_path: Path | str | None = None,
    *,
    brief_path: Path | str | None = None,
) -> str:
    """Index of files and counts. Never inline hashes, patches, or HEAD paths."""
    metrics = pack.get("metrics") or {}
    findings = pack.get("deterministic_findings") or []
    checklist = pack.get("checklist") or []
    ids = [str(item.get("id")) for item in checklist if isinstance(item, dict) and item.get("id")]
    metric_bits = [f"{key}={metrics[key]}" for key in _METRIC_KEYS if key in metrics]
    flag_lines = []
    for finding in findings:
        evidence = finding.get("evidence") or {}
        n_hash = len(evidence.get("commit_hashes") or [])
        summary = finding.get("summary") or ""
        line = f"- `{finding.get('pattern')}` — {n_hash} hashes"
        if summary:
            line += f": {summary}"
        flag_lines.append(line)
    files = []
    if pack_path:
        files.append(f"- Full pack (all hashes, HEAD paths, sampled patches): `{_abs(pack_path)}`")
    if brief_path:
        files.append(f"- Slim brief (metrics + flags + recent sample): `{_abs(brief_path)}`")
    files.append(f"- Repo cwd: `{pack.get('path') or ''}`")
    return (
        f"Repo: `{pack.get('repo_id') or ''}`\n"
        "This message is a catalog. Evidence lives in the files. "
        "Read what a tag needs; do not ingest thousands of commits.\n\n"
        "## Files\n"
        + "\n".join(files)
        + "\n\n## Counts\n"
        f"- commits in pack (allowed_hashes): {len(pack.get('allowed_hashes') or [])}\n"
        f"- recent_commits sampled: {len(pack.get('recent_commits') or [])}\n"
        f"- HEAD paths: {len(pack.get('head_paths') or [])}\n"
        f"- flags: {len(findings)}\n"
        f"- checklist ids: {', '.join(ids) or '(none)'}\n\n"
        "## Metrics (rolled)\n"
        + (", ".join(metric_bits) or "(none)")
        + "\n\n## Flags (names only; hashes are in the pack file)\n"
        + ("\n".join(flag_lines) or "- none")
        + "\n\nRead the slim brief first if present. "
        "Open the full pack only for a hash or path you need. "
        "Then mapper → investigator → scorer.\n"
    )


def executive_prompt(pack: dict) -> str:
    return (
        "Follow the protocol. One executive summary from this pack. No tools.\n\n"
        f"{json.dumps(pack, indent=2, sort_keys=True)}\n"
    )
