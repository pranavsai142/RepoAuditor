"""Roll raw commits into repo + people facts. No git."""

from __future__ import annotations

from datetime import date

from repoauditor.dates import author_utc_date
from repoauditor.roles import classify_tree

EXTRACT_COPY = (
    "head_ref",
    "branch_count",
    "remote_count",
    "head_file_count",
    "tag_count",
)


def _add_volume(bucket: dict, commit: dict) -> None:
    if commit.get("is_merge"):
        return
    if commit.get("additions") is None or commit.get("deletions") is None:
        return
    bucket["additions"] += commit["additions"]
    bucket["deletions"] += commit["deletions"]
    bucket["net"] += commit["additions"] - commit["deletions"]
    bucket["churn"] += commit["additions"] + commit["deletions"]
    bucket["files_changed"] += commit.get("files_changed") or 0


def _empty_cadence() -> dict:
    return {
        "merge_count": 0,
        "non_merge_count": 0,
        "binary_touch_count": 0,
        "unique_paths": set(),
        "weekday_commits": 0,
        "weekend_commits": 0,
        "max_commit_churn": 0,
        "churn_sum": 0,
        "churn_samples": 0,
        "activity_by_day": {},
    }


def _note_cadence(cadence: dict, commit: dict) -> None:
    if commit.get("is_merge"):
        cadence["merge_count"] += 1
    else:
        cadence["non_merge_count"] += 1
    day = author_utc_date(commit["author_date"])
    if day.weekday() < 5:
        cadence["weekday_commits"] += 1
    else:
        cadence["weekend_commits"] += 1
    key = day.isoformat()
    cadence["activity_by_day"][key] = cadence["activity_by_day"].get(key, 0) + 1
    churn = commit.get("churn")
    if churn is not None:
        cadence["churn_sum"] += churn
        cadence["churn_samples"] += 1
        if churn > cadence["max_commit_churn"]:
            cadence["max_commit_churn"] = churn
    for change in commit.get("files") or []:
        path = change.get("path") if isinstance(change, dict) else getattr(change, "path", None)
        if path:
            cadence["unique_paths"].add(path)
        binary = (
            change.get("is_binary")
            if isinstance(change, dict)
            else getattr(change, "is_binary", False)
        )
        if binary:
            cadence["binary_touch_count"] += 1


def _finalize_cadence(row: dict, cadence: dict) -> None:
    by_day = cadence["activity_by_day"]
    weeks: dict[str, int] = {}
    months: dict[str, int] = {}
    for day_s, count in by_day.items():
        day = date.fromisoformat(day_s)
        iso = day.isocalendar()
        week = f"{iso.year}-W{iso.week:02d}"
        weeks[week] = weeks.get(week, 0) + count
        month = day_s[:7]
        months[month] = months.get(month, 0) + count
    first = row.get("first_commit")
    last = row.get("last_commit")
    occupancy = 0
    if first and last:
        occupancy = (author_utc_date(last) - author_utc_date(first)).days + 1
    active_days = len(by_day)
    samples = cadence["churn_samples"]
    commits = row.get("commit_count") or 0
    row.update(
        {
            "merge_count": cadence["merge_count"],
            "non_merge_count": cadence["non_merge_count"],
            "binary_touch_count": cadence["binary_touch_count"],
            "unique_path_count": len(cadence["unique_paths"]),
            "weekday_commits": cadence["weekday_commits"],
            "weekend_commits": cadence["weekend_commits"],
            "max_commit_churn": cadence["max_commit_churn"],
            "mean_commit_churn": round(cadence["churn_sum"] / samples, 2) if samples else 0,
            "occupancy_days": occupancy,
            "active_day_count": active_days,
            "active_week_count": len(weeks),
            "active_month_count": len(months),
            "commits_per_active_day": round(commits / active_days, 2) if active_days else 0,
            "activity_by_day": [{"date": k, "count": v} for k, v in sorted(by_day.items())],
            "activity_by_week": [{"week": k, "count": v} for k, v in sorted(weeks.items())],
            "activity_by_month": [{"month": k, "count": v} for k, v in sorted(months.items())],
        }
    )


def assimilate(
    raw_repos: list[dict],
    commits: list[dict],
    identities: list[dict],
) -> tuple[list[dict], list[dict]]:
    repos = _repo_rolls(raw_repos, commits)
    people = _people_rolls(commits, identities)
    _annotate_people(people, repos, commits)
    return repos, people


def _repo_rolls(raw_repos: list[dict], commits: list[dict]) -> list[dict]:
    by_repo: dict[str, dict] = {}
    cadence_by: dict[str, dict] = {}
    for raw in raw_repos:
        by_repo[raw["repo_id"]] = {
            "repo_id": raw["repo_id"],
            "path": raw["path"],
            "head_paths": raw.get("head_paths", []),
            "readme_excerpt": raw.get("readme_excerpt", ""),
            "tag_count": raw.get("tag_count", 0),
            **{key: raw.get(key, 0 if key != "head_ref" else "") for key in EXTRACT_COPY},
            **classify_tree(raw.get("head_paths") or []),
            "commit_count": 0,
            "human_commit_count": 0,
            "bot_commit_count": 0,
            "human_contributor_count": 0,
            "bot_contributor_count": 0,
            "additions": 0,
            "deletions": 0,
            "net": 0,
            "churn": 0,
            "files_changed": 0,
            "last_commit": None,
            "first_commit": None,
            "authors": {},
        }
        cadence_by[raw["repo_id"]] = _empty_cadence()
    for commit in commits:
        repo = by_repo.setdefault(
            commit["repo_id"],
            {
                "repo_id": commit["repo_id"],
                "path": "",
                "head_paths": [],
                "tag_count": 0,
                "commit_count": 0,
                "human_commit_count": 0,
                "bot_commit_count": 0,
                "human_contributor_count": 0,
                "bot_contributor_count": 0,
                "additions": 0,
                "deletions": 0,
                "net": 0,
                "churn": 0,
                "files_changed": 0,
                "last_commit": None,
                "first_commit": None,
                "authors": {},
            },
        )
        repo["commit_count"] += 1
        if commit.get("is_bot"):
            repo["bot_commit_count"] += 1
        else:
            repo["human_commit_count"] += 1
        _add_volume(repo, commit)
        day = author_utc_date(commit["author_date"]).isoformat()
        if repo["first_commit"] is None or commit["author_date"] < repo["first_commit"]:
            repo["first_commit"] = commit["author_date"]
        if repo["last_commit"] is None or commit["author_date"] > repo["last_commit"]:
            repo["last_commit"] = commit["author_date"]
        key = commit["identity_key"]
        author = repo["authors"].setdefault(
            key,
            {
                "identity_key": key,
                "author_name": commit["author_name"],
                "author_email": commit["author_email"],
                "is_bot": commit.get("is_bot", False),
                "commit_count": 0,
                "churning_non_merge": 0,
                "days": set(),
                "hashes": [],
                "first_commit": None,
                "last_commit": None,
            },
        )
        author["commit_count"] += 1
        author["days"].add(day)
        author["hashes"].append(commit["hash"])
        stamp = commit["author_date"]
        if author["first_commit"] is None or stamp < author["first_commit"]:
            author["first_commit"] = stamp
        if author["last_commit"] is None or stamp > author["last_commit"]:
            author["last_commit"] = stamp
        if not commit.get("is_merge") and (
            (commit.get("additions") or 0) + (commit.get("deletions") or 0) > 0
        ):
            author["churning_non_merge"] += 1
        cadence_by.setdefault(commit["repo_id"], _empty_cadence())
        _note_cadence(cadence_by[commit["repo_id"]], commit)

    rolled = []
    for repo in by_repo.values():
        humans = [a for a in repo["authors"].values() if not a["is_bot"]]
        bots = [a for a in repo["authors"].values() if a["is_bot"]]
        repo["human_contributor_count"] = len(humans)
        repo["bot_contributor_count"] = len(bots)
        repo.update(classify_tree(repo.get("head_paths") or []))
        repo["authors"] = [
            {
                **{k: v for k, v in a.items() if k != "days"},
                "days": sorted(a["days"]),
            }
            for a in repo["authors"].values()
        ]
        _finalize_cadence(repo, cadence_by.get(repo["repo_id"]) or _empty_cadence())
        rolled.append(repo)
    return sorted(rolled, key=lambda r: r["repo_id"])


def _people_rolls(commits: list[dict], identities: list[dict]) -> list[dict]:
    by_key: dict[str, dict] = {}
    cadence_by: dict[str, dict] = {}
    for ident in identities:
        by_key[ident["identity_key"]] = {
            **ident,
            "repos": set(),
            "hashes": [],
            "days": set(),
            "first_commit": None,
            "last_commit": None,
            "additions": 0,
            "deletions": 0,
            "net": 0,
            "churn": 0,
            "files_changed": 0,
            "commit_count": 0,
        }
    for commit in commits:
        key = commit["identity_key"]
        person = by_key.setdefault(
            key,
            {
                "identity_key": key,
                "author_name": commit["author_name"],
                "author_email": commit["author_email"],
                "is_bot": commit.get("is_bot", False),
                "bot_reasons": list(commit.get("bot_reasons") or []),
                "repos": set(),
                "hashes": [],
                "days": set(),
                "first_commit": None,
                "last_commit": None,
                "additions": 0,
                "deletions": 0,
                "net": 0,
                "churn": 0,
                "files_changed": 0,
                "commit_count": 0,
            },
        )
        person["commit_count"] += 1
        person["repos"].add(commit["repo_id"])
        person["hashes"].append({"repo_id": commit["repo_id"], "hash": commit["hash"]})
        person["days"].add(author_utc_date(commit["author_date"]).isoformat())
        if person["first_commit"] is None or commit["author_date"] < person["first_commit"]:
            person["first_commit"] = commit["author_date"]
        if person["last_commit"] is None or commit["author_date"] > person["last_commit"]:
            person["last_commit"] = commit["author_date"]
        _add_volume(person, commit)
        cadence_by.setdefault(key, _empty_cadence())
        _note_cadence(cadence_by[key], commit)
    people = []
    for person in by_key.values():
        rolled = {
            **person,
            "repos": sorted(person["repos"]),
            "repo_count": len(person["repos"]),
            "days": sorted(person["days"]),
            "distinct_days": len(person["days"]),
        }
        _finalize_cadence(rolled, cadence_by.get(person["identity_key"]) or _empty_cadence())
        people.append(rolled)
    return sorted(people, key=lambda p: p["identity_key"])


def _annotate_people(people: list[dict], repos: list[dict], commits: list[dict]) -> None:
    by_id = {r["repo_id"]: r for r in repos}
    occupancy: dict[str, dict[str, list]] = {}
    for commit in commits:
        if commit.get("is_bot"):
            continue
        key = commit.get("identity_key")
        if not key:
            continue
        day = author_utc_date(commit["author_date"])
        occupancy.setdefault(key, {}).setdefault(commit["repo_id"], []).append(day)
    for person in people:
        durable = 0
        thin = 0
        spans = []
        for repo_id in person.get("repos") or []:
            repo = by_id.get(repo_id) or {}
            if repo.get("is_ops"):
                durable += 1
            if repo.get("docs_only") or repo.get("has_requirements") or (
                (repo.get("commit_count") or 0) <= 12 and not repo.get("is_ops")
            ):
                thin += 1
            days = occupancy.get(person["identity_key"], {}).get(repo_id) or []
            if days:
                spans.append((min(days), max(days), (max(days) - min(days)).days + 1, repo_id))
        person["durable_repo_count"] = durable
        person["thin_repo_count"] = thin
        person["occupancy_spans"] = [
            {"repo_id": repo_id, "start": a.isoformat(), "end": b.isoformat(), "days": n}
            for a, b, n, repo_id in spans
        ]
