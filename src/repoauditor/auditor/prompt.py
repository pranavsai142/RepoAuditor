"""Lean investigate + score prompts. User message is a file catalog, not the pack."""

from __future__ import annotations

import json
from pathlib import Path

from repoauditor.auditor.schema import CATEGORIES, CHECKLIST_IDS

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

Rules: open catalog files as needed; do not invent hashes; do not dump every commit into context; do not edit the tree; do not search the web.
End with one JSON object in the shape below. If you cannot, write the summary as plain text.
"""

SCORER_SYSTEM_PROMPT = """\
You only fill a JSON object. You do not investigate. You do not write prose.
Output exactly one JSON object. No markdown. No fences. No keys other than the template.
No text before or after the object.
"""


def checklist_json_shape() -> str:
    items = [
        {
            "id": cid,
            "answer": "",
            "concern": False,
            "evidence_hashes": [],
            "evidence_paths": [],
        }
        for cid in CHECKLIST_IDS
        if cid != "next_inspect"
    ]
    skeleton = {
        "purpose": "",
        "category": "unknown",
        "headline": "",
        "executive_summary": "",
        "checklist": items,
        "next_inspect": [{"hash": "", "why": ""}],
    }
    return (
        "JSON shape (fill every checklist id; category one of "
        + ", ".join(CATEGORIES)
        + "):\n"
        + json.dumps(skeleton, indent=2)
    )

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
        "Then mapper → investigator → scorer.\n\n"
        + checklist_json_shape()
        + "\n"
    )


def scorer_followup_prompt(report: dict, pack: dict) -> str:
    ids = [
        str(item.get("id"))
        for item in pack.get("checklist") or []
        if isinstance(item, dict) and item.get("id")
    ] or [cid for cid in CHECKLIST_IDS if cid != "next_inspect"]
    headline = report.get("headline") or ""
    summary = report.get("executive_summary") or ""
    return (
        "ONLY fill the JSON template at the bottom. Nothing else.\n"
        "Rules (deterministic):\n"
        f"- purpose = one short clause from the notes. category = exactly one of: {', '.join(CATEGORIES)}.\n"
        "- headline = copy the Headline line below, character for character. If empty, first sentence of the notes.\n"
        "- executive_summary = copy the Notes block below, character for character. Do not rewrite it.\n"
        "- checklist: one object per id listed, in that order. Do not add or drop ids.\n"
        "- answer = a sentence grounded in the notes. If the notes do not decide it, answer must start with \"cannot tell\" and concern=false.\n"
        "- concern = true or false only (JSON booleans, not strings).\n"
        "- evidence_hashes = only full hashes that appear in the notes. Else [].\n"
        "- evidence_paths = only paths that appear in the notes. Else [].\n"
        "- next_inspect = 0–3 objects whose hash appears in the notes. Else [].\n"
        "- Do not invent hashes, paths, people, or facts that are not in the notes.\n"
        "- Output the JSON object only.\n\n"
        f"Repo: {pack.get('repo_id') or ''}\n"
        f"Headline: {headline}\n\n"
        "Notes:\n"
        f"{summary}\n\n"
        f"Checklist ids (use all, this order): {', '.join(ids)}\n\n"
        "TEMPLATE — replace empty strings and false/[] only. Keep this key set:\n"
        + json.dumps(_checklist_skeleton(ids), indent=2)
        + "\n"
    )


def _checklist_skeleton(ids: list[str]) -> dict:
    return {
        "purpose": "",
        "category": "unknown",
        "headline": "",
        "executive_summary": "",
        "checklist": [
            {
                "id": cid,
                "answer": "",
                "concern": False,
                "evidence_hashes": [],
                "evidence_paths": [],
            }
            for cid in ids
            if cid != "next_inspect"
        ],
        "next_inspect": [],
    }


def executive_prompt(pack: dict) -> str:
    return (
        "Follow the protocol. One executive summary from this pack. No tools.\n\n"
        f"{json.dumps(pack, indent=2, sort_keys=True)}\n"
    )
