"""Classify whether a commit added code, comments, or docs. Uses git show."""

from __future__ import annotations

from pathlib import Path

from repoauditor.gitcmd import run_git

CODE_EXT = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".go",
    ".rs",
    ".c",
    ".h",
    ".cc",
    ".cpp",
    ".java",
    ".kt",
    ".rb",
    ".php",
    ".cs",
    ".swift",
    ".m",
    ".scala",
    ".sh",
    ".bash",
}
DOC_EXT = {".md", ".rst", ".txt", ".adoc"}
CONFIG_EXT = {".json", ".yml", ".yaml", ".toml", ".ini", ".lock", ".cfg"}


def path_kind(path: str) -> str:
    name = path.rsplit("/", 1)[-1].lower()
    if name.startswith("readme"):
        return "docs"
    dot = name.rfind(".")
    ext = name[dot:] if dot >= 0 else ""
    if ext in DOC_EXT:
        return "docs"
    if ext in CONFIG_EXT:
        return "config"
    if ext in CODE_EXT:
        return "code"
    return "other"


def classify_line(text: str, kind: str) -> str:
    stripped = text.strip()
    if not stripped:
        return "blank"
    if kind == "docs":
        return "docs"
    if kind != "code":
        return kind
    if stripped.startswith(("#", "//", "/*", "*", "--", ";;")):
        return "comment"
    return "code"


def parse_patch(patch: str) -> dict[str, int]:
    counts = {"code": 0, "comment": 0, "docs": 0, "config": 0, "other": 0, "blank": 0}
    kind = "other"
    for line in patch.splitlines():
        if line.startswith("+++ b/"):
            kind = path_kind(line[6:])
            continue
        if line.startswith("+++"):
            continue
        if not line.startswith("+"):
            continue
        bucket = classify_line(line[1:], kind)
        counts[bucket] = counts.get(bucket, 0) + 1
    return counts


def score_counts(counts: dict[str, int]) -> dict:
    added = sum(counts.values())
    code = counts.get("code", 0)
    return {
        "added_lines": added,
        "code_lines": code,
        "comment_lines": counts.get("comment", 0),
        "docs_lines": counts.get("docs", 0),
        "config_lines": counts.get("config", 0),
        "blank_lines": counts.get("blank", 0),
        "no_code": code == 0 and added > 0,
        "comment_or_docs_only": code == 0
        and (counts.get("comment", 0) + counts.get("docs", 0)) > 0,
    }


def show_patch(repo: Path, commit_hash: str) -> str:
    result = run_git(repo, "show", "--format=", "--patch", commit_hash, check=False)
    if result.returncode != 0:
        return ""
    return result.stdout


def score_commit(repo: Path, commit: dict) -> dict:
    if commit.get("is_merge"):
        return {
            "repo_id": commit["repo_id"],
            "hash": commit["hash"],
            "skipped": "merge",
            "no_code": False,
            "comment_or_docs_only": False,
            "added_lines": 0,
            "code_lines": 0,
            "comment_lines": 0,
            "docs_lines": 0,
        }
    patch = show_patch(repo, commit["hash"])
    scored = score_counts(parse_patch(patch))
    scored["repo_id"] = commit["repo_id"]
    scored["hash"] = commit["hash"]
    return scored


def score_repo(repo_path: Path, commits: list[dict], limit: int = 500) -> dict[str, dict]:
    out: dict[str, dict] = {}
    counted = 0
    for commit in commits:
        if counted >= limit:
            break
        if commit.get("is_merge"):
            continue
        row = score_commit(repo_path, commit)
        out[f"{commit['repo_id']}:{commit['hash']}"] = row
        counted += 1
    return out
