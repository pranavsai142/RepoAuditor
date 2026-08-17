"""Inspector tag scores. Sort key for a department dashboard, not a verdict."""

from __future__ import annotations

from repoauditor.auditor.schema import CHECKLIST_IDS

# next_inspect is a pointer, not a diagnostic. It is not in the sum.
SCORED_IDS: tuple[str, ...] = tuple(cid for cid in CHECKLIST_IDS if cid != "next_inspect")

# Short tag: what the item is looking for (the +1 case).
TAGS: dict[str, str] = {
    "purpose": "identifiable purpose",
    "category": "known kind of repo",
    "head_substance": "real code at HEAD",
    "commit_substance": "commits change behavior",
    "readme_match": "README matches the tree",
    "wip_theater": "ships coherent increments",
    "bot_vs_human": "humans do the work",
    "padding": "not attendance commits",
    "occupancy": "stable occupancy",
    "ai_assistance": "human-directed assistance",
    "demo_vs_durable": "durable system, not a demo",
    "run_the_business": "live critical / finished migration",
    "requirements_theater": "more than a spec doc",
    "greenfield_vs_buy": "not a half-baked suite replacement",
    "next_inspect": "where to look first (unscored)",
}


def rubric_label(cid: str) -> str:
    """Same label on the scorecard and in the repo table columns."""
    return cid.replace("_", " ")


def item_status(item: dict | None) -> str:
    if not item:
        return "unknown"
    if item.get("concern"):
        return "concern"
    answer = (item.get("answer") or "").strip().lower()
    if not answer or "cannot tell" in answer:
        return "unknown"
    return "ok"


def item_score(item: dict | None) -> int | None:
    """+1 ok, 0 cannot tell, -1 concern. None if the item is absent (no analyze)."""
    if not item:
        return None
    status = item_status(item)
    if status == "ok":
        return 1
    if status == "concern":
        return -1
    return 0


def checklist_by_id(report: dict | None) -> dict[str, dict]:
    if not report:
        return {}
    return {row.get("id"): row for row in report.get("checklist") or [] if row.get("id")}


def repo_tag_scores(report: dict | None) -> dict[str, int | None]:
    by_id = checklist_by_id(report)
    if not by_id:
        return {cid: None for cid in SCORED_IDS}
    return {cid: item_score(by_id[cid]) if cid in by_id else 0 for cid in SCORED_IDS}


def inspector_score(report: dict | None) -> int | None:
    scores = repo_tag_scores(report)
    values = [v for v in scores.values() if v is not None]
    if not values:
        return None
    return sum(int(v) for v in values)
