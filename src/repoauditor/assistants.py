"""Label coding-assistant fingerprints in the git record. Not a verdict."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def assistant_catalog() -> list[dict]:
    path = Path(__file__).with_name("assistants.json")
    return json.loads(path.read_text(encoding="utf-8"))["assistants"]


def classify_assistants(commit: dict) -> list[dict]:
    blob_email = f"{commit.get('author_email') or ''} {commit.get('committer_email') or ''}".lower()
    blob_name = f"{commit.get('author_name') or ''} {commit.get('committer_name') or ''}".lower()
    blob_subject = (commit.get("subject") or "").lower()
    blob_trailers = (commit.get("trailers") or "").lower()
    hits = []
    for spec in assistant_catalog():
        reasons = []
        if any(s.lower() in blob_email for s in spec.get("email_substrings") or []):
            reasons.append("email")
        if any(s.lower() in blob_name for s in spec.get("name_substrings") or []):
            reasons.append("name")
        if any(s.lower() in blob_trailers for s in spec.get("trailer_substrings") or []):
            reasons.append("trailer")
        if any(s.lower() in blob_subject for s in spec.get("subject_substrings") or []):
            reasons.append("subject")
        if reasons:
            hits.append({"id": spec["id"], "reasons": reasons})
    return hits


def apply_assistants(commits: list[dict]) -> None:
    for commit in commits:
        hits = classify_assistants(commit)
        commit["assistants"] = hits
        commit["ai_assisted"] = bool(hits)


def assistance_inventory(commits: list[dict]) -> dict:
    by_id: dict[str, dict] = {}
    for commit in commits:
        for hit in commit.get("assistants") or []:
            entry = by_id.setdefault(
                hit["id"],
                {
                    "id": hit["id"],
                    "commit_count": 0,
                    "repos": set(),
                    "identities": set(),
                },
            )
            entry["commit_count"] += 1
            entry["repos"].add(commit.get("repo_id"))
            entry["identities"].add(commit.get("identity_key") or "")
    assistants = []
    for entry in by_id.values():
        assistants.append(
            {
                "id": entry["id"],
                "commit_count": entry["commit_count"],
                "repos": sorted(r for r in entry["repos"] if r),
                "identities": sorted(i for i in entry["identities"] if i),
                "repo_count": len([r for r in entry["repos"] if r]),
            }
        )
    assistants.sort(key=lambda a: (-a["commit_count"], a["id"]))
    return {
        "assistants": assistants,
        "ai_assisted_commits": sum(1 for c in commits if c.get("ai_assisted")),
        "commit_count": len(commits),
        "note": (
            "Assistance fingerprints from authors, committers, subjects, and trailers. "
            "Presence of a signature is not proof a human did no work."
        ),
    }
