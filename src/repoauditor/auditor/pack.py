"""Build the evidence pack handed to the repo-analysis agent."""

from __future__ import annotations

from pathlib import Path

from repoauditor.auditor.prompt import load_checklist
from repoauditor.auditor.substance import path_kind, show_patch
from repoauditor.gitcmd import run_git

README_NAMES = ("README.md", "README", "README.rst", "README.txt")
MAX_COMMITS = 12
MAX_PATCH_CHARS = 2500
MAX_README_CHARS = 2500
MAX_FILE_CHARS = 2000
MAX_SOURCE_SAMPLES = 3


def _safe_name(repo_id: str) -> str:
    return repo_id.replace("/", "__") or "root"


def read_readme(repo_path: Path, head_paths: list[str]) -> dict:
    present = [name for name in README_NAMES if name in head_paths or any(p.endswith("/" + name) for p in head_paths)]
    for name in README_NAMES:
        result = run_git(repo_path, "show", f"HEAD:{name}", check=False)
        if result.returncode == 0 and result.stdout:
            text = result.stdout
            return {
                "path": name,
                "text": text[:MAX_README_CHARS],
                "truncated": len(text) > MAX_README_CHARS,
            }
    return {"path": None, "text": "", "truncated": False, "candidates": present}


def show_head_file(repo_path: Path, rel: str, limit: int = MAX_FILE_CHARS) -> dict:
    result = run_git(repo_path, "show", f"HEAD:{rel}", check=False)
    if result.returncode != 0 or not result.stdout:
        return {"path": rel, "text": "", "truncated": False}
    text = result.stdout
    return {"path": rel, "text": text[:limit], "truncated": len(text) > limit}


def collect_file_excerpts(repo_path: Path, head_paths: list[str], workflow_paths: list[str]) -> tuple[list[dict], list[dict]]:
    workflows = [show_head_file(repo_path, p) for p in workflow_paths[:8]]
    sources = []
    for path in head_paths:
        if path_kind(path) != "code":
            continue
        sources.append(show_head_file(repo_path, path))
        if len(sources) >= MAX_SOURCE_SAMPLES:
            break
    return workflows, sources


def head_kinds(head_paths: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in head_paths:
        kind = path_kind(path)
        counts[kind] = counts.get(kind, 0) + 1
    return counts


def build_repo_pack(
    repo: dict,
    commits: list[dict],
    findings: list[dict],
    substance: dict[str, dict],
    repo_path: Path,
) -> dict:
    rows = [c for c in commits if c["repo_id"] == repo["repo_id"]]
    rows = sorted(rows, key=lambda c: c.get("author_date") or "", reverse=True)
    sample = []
    for commit in rows[:MAX_COMMITS]:
        key = f"{commit['repo_id']}:{commit['hash']}"
        patch = show_patch(repo_path, commit["hash"]) if not commit.get("is_merge") else ""
        sample.append(
            {
                "hash": commit["hash"],
                "author_name": commit.get("author_name"),
                "author_email": commit.get("author_email"),
                "author_date": commit.get("author_date"),
                "subject": commit.get("subject"),
                "is_bot": commit.get("is_bot", False),
                "is_merge": commit.get("is_merge", False),
                "additions": commit.get("additions"),
                "deletions": commit.get("deletions"),
                "files": [f.get("path") for f in commit.get("files") or []],
                "substance": substance.get(key),
                "patch_excerpt": patch[:MAX_PATCH_CHARS],
            }
        )
    repo_findings = [f for f in findings if f.get("subject_id") == repo["repo_id"]]
    head_paths = repo.get("head_paths") or []
    workflows = [
        p
        for p in head_paths
        if ".github/workflows/" in p or p.endswith("Jenkinsfile") or p.endswith(".gitlab-ci.yml")
    ]
    workflow_files, source_samples = collect_file_excerpts(repo_path, head_paths, workflows)
    return {
        "repo_id": repo["repo_id"],
        "path": str(repo_path),
        "metrics": {
            "commit_count": repo.get("commit_count"),
            "human_contributor_count": repo.get("human_contributor_count"),
            "bot_contributor_count": repo.get("bot_contributor_count"),
            "additions": repo.get("additions"),
            "deletions": repo.get("deletions"),
            "net": repo.get("net"),
            "churn": repo.get("churn"),
            "files_changed": repo.get("files_changed"),
            "first_commit": repo.get("first_commit"),
            "last_commit": repo.get("last_commit"),
            "tag_count": repo.get("tag_count"),
        },
        "head_paths": repo.get("head_paths") or [],
        "head_kinds": head_kinds(repo.get("head_paths") or []),
        "readme": read_readme(repo_path, repo.get("head_paths") or []),
        "workflow_paths": workflows,
        "workflow_files": workflow_files,
        "source_samples": source_samples,
        "is_ops": repo.get("is_ops", False),
        "docs_only": repo.get("docs_only", False),
        "has_requirements": repo.get("has_requirements", False),
        "deterministic_findings": repo_findings,
        "recent_commits": sample,
        "allowed_hashes": [c["hash"] for c in rows],
        "checklist": load_checklist(),
        "instructions": (
            "Cite hashes from allowed_hashes in this file. "
            "Open the repo for files a tag needs. Do not invent hashes."
        ),
    }


def brief_for_grok(pack: dict, *, hash_cap: int = 40, path_cap: int = 40) -> dict:
    """Smaller pack for the model: drop full hash/path dumps, keep what scoring needs."""
    hashes: list[str] = []
    for commit in pack.get("recent_commits") or []:
        if commit.get("hash"):
            hashes.append(commit["hash"])
    for finding in pack.get("deterministic_findings") or []:
        hashes.extend((finding.get("evidence") or {}).get("commit_hashes") or [])
    seen: list[str] = []
    for commit_hash in hashes:
        if commit_hash not in seen:
            seen.append(commit_hash)
        if len(seen) >= hash_cap:
            break
    findings = []
    for finding in pack.get("deterministic_findings") or []:
        evidence = dict(finding.get("evidence") or {})
        evidence["commit_hashes"] = (evidence.get("commit_hashes") or [])[:8]
        findings.append(
            {
                "pattern": finding.get("pattern"),
                "summary": finding.get("summary"),
                "evidence": evidence,
            }
        )
    commits = []
    for commit in pack.get("recent_commits") or []:
        row = dict(commit)
        patch = row.get("patch_excerpt") or ""
        if len(patch) > 1200:
            row["patch_excerpt"] = patch[:1200]
            row["patch_truncated"] = True
        commits.append(row)
    paths = pack.get("head_paths") or []
    return {
        "repo_id": pack.get("repo_id"),
        "path": pack.get("path"),
        "metrics": pack.get("metrics"),
        "head_kinds": pack.get("head_kinds"),
        "head_path_count": len(paths),
        "head_path_sample": paths[:path_cap],
        "readme": pack.get("readme"),
        "source_samples": pack.get("source_samples"),
        "workflow_files": pack.get("workflow_files"),
        "is_ops": pack.get("is_ops"),
        "docs_only": pack.get("docs_only"),
        "has_requirements": pack.get("has_requirements"),
        "deterministic_findings": findings,
        "recent_commits": commits,
        "allowed_hashes": seen,
        "checklist": pack.get("checklist"),
    }


def build_department_pack(
    repos: list[dict],
    people: list[dict],
    findings: list[dict],
    rankings: dict,
    assistance: dict,
    input_path: str,
    as_of: str,
) -> dict:
    by_pattern: dict[str, int] = {}
    for finding in findings:
        by_pattern[finding["pattern"]] = by_pattern.get(finding["pattern"], 0) + 1
    humans = [p for p in people if not p.get("is_bot")]
    return {
        "scope": "department",
        "input_path": input_path,
        "as_of": as_of,
        "repo_count": len(repos),
        "human_count": len(humans),
        "finding_counts": by_pattern,
        "assistance": assistance,
        "rankings": rankings,
        "repos": [
            {
                "repo_id": r["repo_id"],
                "is_ops": r.get("is_ops"),
                "docs_only": r.get("docs_only"),
                "has_requirements": r.get("has_requirements"),
                "commit_count": r.get("commit_count"),
                "human_contributor_count": r.get("human_contributor_count"),
                "last_commit": r.get("last_commit"),
                "churn": r.get("churn"),
                "additions": r.get("additions"),
                "deletions": r.get("deletions"),
            }
            for r in repos
        ],
        "people": [
            {
                "name": p.get("author_name"),
                "email": p.get("author_email"),
                "durable_repo_count": p.get("durable_repo_count"),
                "thin_repo_count": p.get("thin_repo_count"),
                "repo_count": p.get("repo_count"),
                "commit_count": p.get("commit_count"),
                "last_commit": p.get("last_commit"),
                "repos": p.get("repos"),
            }
            for p in sorted(
                humans,
                key=lambda x: (x.get("durable_repo_count") or 0, x.get("churn") or 0),
                reverse=True,
            )[:40]
        ],
        "findings": [
            {
                "pattern": f.get("pattern"),
                "lens": f.get("lens"),
                "subject_id": f.get("subject_id"),
                "summary": f.get("summary"),
            }
            for f in findings
        ],
        "instructions": (
            "Write the executive summary. Comprehend every metric in this pack. "
            "Separate run-the-business shared services from hackathon/demo/requirements theater. "
            "Name who appears to carry durable systems vs who hops thin greenfields. "
            "unscriptable = what only reading code/workflows/README can say."
        ),
    }
