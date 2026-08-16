from __future__ import annotations


def _known_hashes(pack: dict) -> set[str]:
    return set(pack.get("allowed_hashes") or [])


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
        kept_h = [h for h in item.get("evidence_hashes") or [] if keep_hash(h)]
        checklist.append({**item, "evidence_hashes": kept_h})
    next_inspect = []
    for item in report.get("next_inspect") or []:
        if keep_hash(item.get("hash") or ""):
            next_inspect.append(item)
        # invented inspect hashes are dropped
    return {
        "repo_id": pack.get("repo_id"),
        "purpose": report.get("purpose") or "",
        "category": report.get("category") or "unknown",
        "checklist": checklist,
        "next_inspect": next_inspect,
        "stripped_unknown_hashes": stripped,
    }
