"""Lean investigate + score prompts. User message is a file catalog, not the pack."""

from __future__ import annotations

import json
from pathlib import Path

from repoauditor.auditor.schema import CATEGORIES, CHECKLIST_IDS

SYSTEM_PROMPT = """\
Inspect one git repo (cwd). User message is a file catalog — read those files; do not inline the pack.

Mapper: HEAD vs claims (README, tree, sampled source). Inform purpose, category, head_substance, readme_match.
Investigator: follow pack flags in the tree; do not stop at the README. Inform commit_substance, wip_theater, bot_vs_human, padding, occupancy, ai_assistance. Cite pack hashes/paths only.
Scorer: every checklist id. concern=true → −1; answer starts with "cannot tell" → 0; else +1. Also demo_vs_durable, run_the_business, requirements_theater, greenfield_vs_buy.
Summary last: headline + executive_summary for this repo. No length cap. Not a README restatement. Not a list of tag names.
Cover what it does (HEAD vs claims), whether it is used and how, who works it, meta-history. Ordinary readings (fork, student work, research iteration) when the files support them. Dates, people, paths. Volume is not work.

This call outputs one JSON object (keys in the user message): filled checklist + headline + executive_summary. Do not invent hashes. Do not wait for a follow-up.
"""

SYSTEM_PROMPT_SUBAGENTS = (
    "Mapper/investigator may use explore children; you still score and write the JSON.\n"
    + SYSTEM_PROMPT
)

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
    return (
        f"Repo {pack.get('repo_id') or ''}\n"
        f"pack {_abs(pack_path) if pack_path else ''}\n"
        f"brief {_abs(brief_path) if brief_path else ''}\n"
        f"tree {pack.get('path') or ''}\n"
        f"n_hash={len(pack.get('allowed_hashes') or [])} "
        f"n_recent={len(pack.get('recent_commits') or [])} "
        f"n_paths={len(pack.get('head_paths') or [])} "
        f"n_flags={len(findings)}\n"
        f"ids {', '.join(ids) or '-'}\n"
        f"metrics {', '.join(metric_bits) or '-'}\n"
        f"flags {'; '.join(flag_lines) or '-'}\n"
        "Read brief then only pack/tree a tag needs. "
        "JSON this call: purpose,category,headline,executive_summary,"
        "checklist[{id,answer,concern,evidence_hashes,evidence_paths}],"
        "next_inspect[{hash,why}]. Every id. No invented hashes.\n"
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
