from __future__ import annotations

from repoauditor.auditor.schema import CATEGORIES, CHECKLIST_IDS

_CHECKLIST_IDS = set(CHECKLIST_IDS)
_CATEGORIES = set(CATEGORIES)


def _known_hashes(pack: dict) -> set[str]:
    return set(pack.get("allowed_hashes") or [])


def _str_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [v for v in values if isinstance(v, str) and v]


def validate_report(report: dict, pack: dict) -> dict:
    hashes = _known_hashes(pack)
    stripped: list[str] = []

    def keep_hash(value: str) -> bool:
        if value in hashes:
            return True
        if value:
            stripped.append(value)
        return False

    checklist = []
    for item in report.get("checklist") or []:
        if not isinstance(item, dict):
            continue
        cid = item.get("id")
        if cid not in _CHECKLIST_IDS:
            continue
        kept_h = [h for h in _str_list(item.get("evidence_hashes")) if keep_hash(h)]
        checklist.append(
            {
                "id": cid,
                "answer": item.get("answer") or "",
                "concern": bool(item.get("concern")),
                "evidence_hashes": kept_h,
                "evidence_paths": _str_list(item.get("evidence_paths")),
            }
        )
    next_inspect = []
    for item in report.get("next_inspect") or []:
        if not isinstance(item, dict):
            continue
        commit = item.get("hash") or ""
        if keep_hash(commit):
            next_inspect.append({"hash": commit, "why": item.get("why") or ""})
        # invented inspect hashes are dropped
    category = report.get("category") or "unknown"
    if category not in _CATEGORIES:
        category = "unknown"
    return {
        "repo_id": pack.get("repo_id"),
        "purpose": report.get("purpose") or "",
        "category": category,
        "headline": report.get("headline") or "",
        "executive_summary": report.get("executive_summary") or "",
        "checklist": checklist,
        "next_inspect": next_inspect,
        "stripped_unknown_hashes": stripped,
    }
