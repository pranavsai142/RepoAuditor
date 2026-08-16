"""Rank repos and people. Entry points, not a health score. No git."""

from __future__ import annotations


def rank(repos: list[dict], people: list[dict]) -> dict:
    def last_key(row: dict) -> str:
        return row.get("last_commit") or ""

    humans = [p for p in people if not p.get("is_bot")]
    return {
        "repos": {
            "by_last_commit": [
                r["repo_id"] for r in sorted(repos, key=last_key)
            ],
            "by_churn": [
                r["repo_id"] for r in sorted(repos, key=lambda r: r.get("churn") or 0, reverse=True)
            ],
            "by_human_contributors": [
                r["repo_id"]
                for r in sorted(repos, key=lambda r: r.get("human_contributor_count") or 0)
            ],
        },
        "people": {
            "by_last_commit": [
                p["identity_key"] for p in sorted(humans, key=last_key)
            ],
            "by_churn": [
                p["identity_key"]
                for p in sorted(humans, key=lambda p: p.get("churn") or 0, reverse=True)
            ],
            "by_repo_count": [
                p["identity_key"]
                for p in sorted(humans, key=lambda p: p.get("repo_count") or 0, reverse=True)
            ],
            "by_durable_repos": [
                p["identity_key"]
                for p in sorted(
                    humans,
                    key=lambda p: (p.get("durable_repo_count") or 0, p.get("churn") or 0),
                    reverse=True,
                )
            ],
        },
        "note": (
            "Rankings are entry points. Commit authors only "
            "(not issues, reviews, or chat). Lines are decomposed "
            "as additions/deletions/net/churn/files_changed."
        ),
    }
