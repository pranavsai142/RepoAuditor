from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from repoauditor.dates import author_utc_date, days_before
from repoauditor.patterns import thresholds as T


def detect_all(
    repos: list[dict],
    people: list[dict],
    commits: list[dict],
    as_of: date,
    substance: dict[str, dict] | None = None,
) -> list[dict]:
    by_repo: dict[str, list[dict]] = defaultdict(list)
    for commit in commits:
        by_repo[commit["repo_id"]].append(commit)
    findings: list[dict] = []
    for repo in repos:
        rows = by_repo.get(repo["repo_id"], [])
        findings.extend(_readme_husk(repo, rows))
        findings.extend(_perpetual_wip(repo, rows))
        findings.extend(_bot_operated(repo, rows))
        findings.extend(_commit_padding(repo, rows))
        findings.extend(_hot_potato(repo, rows))
        findings.extend(_one_person_island(repo, rows))
        findings.extend(_burst_graveyard(repo, rows, as_of))
        findings.extend(_low_substance(repo, rows, substance or {}))
        findings.extend(_ai_dominated(repo, rows))
        findings.extend(_demo_replacement(repo, rows))
        findings.extend(_requirements_theater(repo, rows))
    for person in people:
        findings.extend(_contributor_fade(person, as_of))
        findings.extend(_greenfield_hop(person))
    return findings


def _finding(
    pattern: str,
    lens: str,
    subject_id: str,
    summary: str,
    hashes: list[str],
    metrics: dict,
) -> dict:
    return {
        "pattern": pattern,
        "lens": lens,
        "subject_id": subject_id,
        "summary": summary,
        "evidence": {
            "commit_hashes": hashes,
            "metrics": metrics,
        },
    }


def _readme_husk(repo: dict, commits: list[dict]) -> list[dict]:
    if repo["commit_count"] > T.HUSK_MAX_COMMITS:
        return []
    paths = repo.get("head_paths") or []
    if paths and not all(T.is_husk_path(p) for p in paths):
        return []
    hashes = [c["hash"] for c in commits]
    if not hashes:
        return []
    return [
        _finding(
            "readme_husk",
            "repo",
            repo["repo_id"],
            "HEAD tree is empty or docs/meta only, with very few commits.",
            hashes,
            {"commit_count": repo["commit_count"], "head_paths": paths},
        )
    ]


def _perpetual_wip(repo: dict, commits: list[dict]) -> list[dict]:
    if repo["commit_count"] < T.WIP_MIN_COMMITS:
        return []
    matching = [c for c in commits if T.WIP_RE.search(c.get("subject") or "")]
    share = len(matching) / repo["commit_count"]
    if share < T.WIP_SUBJECT_SHARE:
        return []
    if repo.get("tag_count", 0) > 0:
        return []
    return [
        _finding(
            "perpetual_wip",
            "repo",
            repo["repo_id"],
            "A majority of subjects match WIP and the repo has no tags.",
            [c["hash"] for c in matching],
            {
                "commit_count": repo["commit_count"],
                "wip_count": len(matching),
                "wip_share": share,
                "tag_count": repo.get("tag_count", 0),
            },
        )
    ]


def _bot_operated(repo: dict, commits: list[dict]) -> list[dict]:
    if repo["commit_count"] < T.BOT_MIN_COMMITS:
        return []
    human_share = repo["human_commit_count"] / repo["commit_count"]
    if human_share >= T.BOT_HUMAN_SHARE_MAX:
        return []
    bots = [c["hash"] for c in commits if c.get("is_bot")]
    humans = [c["hash"] for c in commits if not c.get("is_bot")]
    return [
        _finding(
            "bot_operated",
            "repo",
            repo["repo_id"],
            "Most commits are labeled bot; human share is below the v1 threshold.",
            bots + humans,
            {
                "human_share": human_share,
                "bot_commit_count": repo["bot_commit_count"],
                "human_commit_count": repo["human_commit_count"],
                "bot_hashes": bots,
                "human_hashes": humans,
            },
        )
    ]


def _commit_padding(repo: dict, commits: list[dict]) -> list[dict]:
    humans = [c for c in commits if not c.get("is_bot")]
    human_keys = {c["identity_key"] for c in humans}
    if len(human_keys) != 1 or len(humans) < T.PADDING_MIN_COMMITS:
        return []
    by_day: dict[str, int] = defaultdict(int)
    for commit in humans:
        by_day[author_utc_date(commit["author_date"]).isoformat()] += 1
    solo_days = [d for d, n in by_day.items() if n == 1]
    if len(solo_days) < T.PADDING_MIN_SOLO_DAYS:
        return []
    clusters: dict[str, list[str]] = defaultdict(list)
    for commit in humans:
        if commit.get("tree"):
            clusters[f"tree:{commit['tree']}"].append(commit["hash"])
        if commit.get("patch_id"):
            clusters[f"patch:{commit['patch_id']}"].append(commit["hash"])
    if not clusters:
        return []
    key, hashes = max(clusters.items(), key=lambda kv: len(set(kv[1])))
    unique = list(dict.fromkeys(hashes))
    share = len(unique) / len(humans)
    if len(unique) < T.PADDING_CLUSTER_MIN and share < T.PADDING_CLUSTER_SHARE:
        return []
    if len(unique) < T.PADDING_CLUSTER_MIN:
        return []
    return [
        _finding(
            "commit_padding",
            "repo",
            repo["repo_id"],
            "One human, regular single-commit days, and a large same-contents cluster.",
            unique,
            {
                "solo_days": sorted(solo_days),
                "cluster_key": key,
                "cluster_size": len(unique),
                "human_commits": len(humans),
            },
        )
    ]


def _occupancy_streaks(commits: list[dict]) -> list[dict]:
    """Maximal daily runs per human (gaps > 1 day break a streak)."""
    by_human: dict[str, set[date]] = defaultdict(set)
    hashes_on: dict[tuple[str, date], list[str]] = defaultdict(list)
    for commit in commits:
        if commit.get("is_bot"):
            continue
        day = author_utc_date(commit["author_date"])
        by_human[commit["identity_key"]].add(day)
        hashes_on[(commit["identity_key"], day)].append(commit["hash"])
    streaks = []
    for key, days in by_human.items():
        ordered = sorted(days)
        start = ordered[0]
        prev = ordered[0]
        for day in ordered[1:]:
            if (day - prev).days == 1:
                prev = day
                continue
            streaks.append(_streak(key, start, prev, hashes_on))
            start = day
            prev = day
        streaks.append(_streak(key, start, prev, hashes_on))
    streaks.sort(key=lambda s: s["start"])
    return streaks


def _streak(key: str, start: date, end: date, hashes_on: dict) -> dict:
    hashes = []
    day = start
    while day <= end:
        hashes.extend(hashes_on.get((key, day), []))
        day += timedelta(days=1)
    return {
        "identity_key": key,
        "start": start,
        "end": end,
        "length": (end - start).days + 1,
        "hashes": hashes,
    }


def _hot_potato(repo: dict, commits: list[dict]) -> list[dict]:
    humans = {c["identity_key"] for c in commits if not c.get("is_bot")}
    if len(humans) < 2:
        return []
    streaks = [
        s
        for s in _occupancy_streaks(commits)
        if T.HOT_STREAK_MIN <= s["length"] <= T.HOT_STREAK_MAX
    ]
    for i, first in enumerate(streaks):
        for second in streaks[i + 1 :]:
            if second["identity_key"] == first["identity_key"]:
                continue
            gap = (second["start"] - first["end"]).days - 1
            if gap >= T.HOT_GAP_MIN:
                hashes = []
                if first["hashes"]:
                    hashes.append(first["hashes"][0])
                    hashes.append(first["hashes"][-1])
                if second["hashes"]:
                    hashes.append(second["hashes"][0])
                    hashes.append(second["hashes"][-1])
                return [
                    _finding(
                        "hot_potato",
                        "repo",
                        repo["repo_id"],
                        "One human occupied the repo, then a gap, then a different human.",
                        list(dict.fromkeys(hashes)),
                        {
                            "first": {
                                "identity_key": first["identity_key"],
                                "start": first["start"].isoformat(),
                                "end": first["end"].isoformat(),
                            },
                            "second": {
                                "identity_key": second["identity_key"],
                                "start": second["start"].isoformat(),
                                "end": second["end"].isoformat(),
                            },
                            "gap_days": gap,
                        },
                    )
                ]
    return []


def _one_person_island(repo: dict, commits: list[dict]) -> list[dict]:
    humans = [a for a in repo.get("authors") or [] if not a.get("is_bot")]
    churning = [a for a in humans if a.get("churning_non_merge", 0) > 0]
    human_commits = sum(a["commit_count"] for a in humans)
    if len(churning) != 1 or human_commits < T.ISLAND_MIN_HUMAN_COMMITS:
        return []
    hashes = [c["hash"] for c in commits if not c.get("is_bot")]
    return [
        _finding(
            "one_person_island",
            "repo",
            repo["repo_id"],
            "Exactly one human produced the non-merge churning commits.",
            hashes,
            {
                "human_contributor_count": len(humans),
                "human_commit_count": human_commits,
                "authors": [
                    {
                        "identity_key": a["identity_key"],
                        "commit_count": a["commit_count"],
                        "is_bot": a.get("is_bot", False),
                    }
                    for a in repo.get("authors") or []
                ],
            },
        )
    ]


def _burst_graveyard(repo: dict, commits: list[dict], as_of: date) -> list[dict]:
    if not commits:
        return []
    days = sorted(author_utc_date(c["author_date"]) for c in commits)
    last = days[-1]
    if days_before(last, as_of) < T.BURST_SILENCE:
        return []
    by_day: dict[date, list[str]] = defaultdict(list)
    for commit in commits:
        by_day[author_utc_date(commit["author_date"])].append(commit["hash"])
    unique_days = sorted(by_day)
    best_hashes: list[str] = []
    left = 0
    for right, day in enumerate(unique_days):
        while (day - unique_days[left]).days > T.BURST_WINDOW_DAYS - 1:
            left += 1
        window_hashes = []
        for d in unique_days[left : right + 1]:
            window_hashes.extend(by_day[d])
        if len(window_hashes) > len(best_hashes):
            best_hashes = window_hashes
    if len(best_hashes) < T.BURST_MIN_COMMITS:
        return []
    return [
        _finding(
            "burst_graveyard",
            "repo",
            repo["repo_id"],
            "A short burst of commits is followed by a long silence before the as-of date.",
            best_hashes,
            {
                "burst_commits": len(best_hashes),
                "last_commit": last.isoformat(),
                "as_of": as_of.isoformat(),
                "silence_days": days_before(last, as_of),
            },
        )
    ]


def _ai_dominated(repo: dict, commits: list[dict]) -> list[dict]:
    if len(commits) < T.AI_MIN_COMMITS:
        return []
    assisted = [c for c in commits if c.get("ai_assisted")]
    share = len(assisted) / len(commits)
    if share < T.AI_SHARE:
        return []
    kinds = sorted({hit["id"] for c in assisted for hit in c.get("assistants") or []})
    return [
        _finding(
            "ai_dominated",
            "repo",
            repo["repo_id"],
            "Most commits carry a coding-assistant fingerprint (trailer, author, or subject).",
            [c["hash"] for c in assisted],
            {
                "ai_share": share,
                "ai_commits": len(assisted),
                "commit_count": len(commits),
                "assistants": kinds,
            },
        )
    ]


def _demo_replacement(repo: dict, commits: list[dict]) -> list[dict]:
    excerpt = repo.get("readme_excerpt") or ""
    subjects = " ".join(c.get("subject") or "" for c in commits)
    claims = bool(T.REPLACE_RE.search(excerpt) or T.REPLACE_RE.search(subjects))
    if not claims:
        return []
    paths = [p.lower() for p in repo.get("head_paths") or []]
    markers = [m for m in T.SCAFFOLD_MARKERS if any(p.endswith(m.lower()) or p == m.lower() for p in paths)]
    if len(markers) < 2:
        return []
    hashes = [c["hash"] for c in commits[:8]]
    return [
        _finding(
            "demo_replacement",
            "repo",
            repo["repo_id"],
            "README/subjects talk about replacing a system, but HEAD looks like a scaffolded demo.",
            hashes,
            {"scaffold_markers": markers, "claim_excerpt": excerpt[:240]},
        )
    ]


def _requirements_theater(repo: dict, commits: list[dict]) -> list[dict]:
    if not repo.get("has_requirements") or not repo.get("docs_only"):
        return []
    if repo.get("commit_count", 0) < 2:
        return []
    return [
        _finding(
            "requirements_theater",
            "repo",
            repo["repo_id"],
            "The tree is requirements/spec markdown with no product or ops code.",
            [c["hash"] for c in commits],
            {
                "requirements_paths": repo.get("requirements_paths") or [],
                "commit_count": repo.get("commit_count"),
            },
        )
    ]


def _greenfield_hop(person: dict) -> list[dict]:
    if person.get("is_bot"):
        return []
    spans = person.get("occupancy_spans") or []
    if len(spans) < T.HOP_MIN_REPOS:
        return []
    short = [s for s in spans if s.get("days", 0) <= T.HOP_MAX_SPAN_DAYS]
    if len(short) < T.HOP_MIN_REPOS:
        return []
    if (person.get("thin_repo_count") or 0) < 2:
        return []
    hashes = []
    for item in person.get("hashes") or []:
        if isinstance(item, dict):
            hashes.append(item["hash"])
        else:
            hashes.append(item)
    if not hashes:
        return []
    return [
        _finding(
            "greenfield_hop",
            "person",
            person["identity_key"],
            "Short occupancy on several thin/greenfield repos — project hop, not a durable system.",
            hashes,
            {
                "repos": [s["repo_id"] for s in short],
                "thin_repo_count": person.get("thin_repo_count"),
                "durable_repo_count": person.get("durable_repo_count"),
            },
        )
    ]


def _low_substance(repo: dict, commits: list[dict], substance: dict[str, dict]) -> list[dict]:
    if repo.get("is_ops"):
        return []
    scored = []
    for commit in commits:
        if commit.get("is_merge"):
            continue
        row = substance.get(f"{commit['repo_id']}:{commit['hash']}")
        if not row:
            continue
        scored.append((commit, row))
    if len(scored) < T.SUBSTANCE_MIN_COMMITS:
        return []
    empty = [c for c, row in scored if row.get("no_code")]
    share = len(empty) / len(scored)
    if share < T.SUBSTANCE_NO_CODE_SHARE:
        return []
    return [
        _finding(
            "low_substance",
            "repo",
            repo["repo_id"],
            "Most sampled commits add no code lines — comments, docs, or empty churn.",
            [c["hash"] for c in empty],
            {
                "sampled": len(scored),
                "no_code_commits": len(empty),
                "no_code_share": share,
            },
        )
    ]


def _contributor_fade(person: dict, as_of: date) -> list[dict]:
    if person.get("is_bot"):
        return []
    days = [date.fromisoformat(d) for d in person.get("days") or []]
    if len(days) < T.FADE_MIN_DAYS:
        return []
    first, last = min(days), max(days)
    span = (last - first).days
    if span < T.FADE_MIN_SPAN:
        return []
    density = len(days) / span if span else 0
    if density < T.FADE_DENSITY:
        return []
    if days_before(last, as_of) < T.FADE_SILENCE:
        return []
    hashes = [item["hash"] if isinstance(item, dict) else item for item in person.get("hashes") or []]
    if not hashes:
        return []
    return [
        _finding(
            "contributor_fade",
            "person",
            person["identity_key"],
            "Regular commit-days over a span, then silence before the as-of date.",
            hashes,
            {
                "distinct_days": len(days),
                "span_days": span,
                "density": density,
                "last_commit": last.isoformat(),
                "as_of": as_of.isoformat(),
                "silence_days": days_before(last, as_of),
            },
        )
    ]
