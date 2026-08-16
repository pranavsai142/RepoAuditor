"""Extract the commit fact table using the locked first-party git argv."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from repoauditor.gitcmd import git_version, run_git
from repoauditor.models import Commit, FileChange, to_dict, volume_of

LOG_FORMAT = "%x1e%H%x00%T%x00%P%x00%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI%x00%s"

LOG_ARGV = [
    "-c",
    "i18n.logOutputEncoding=UTF-8",
    "log",
    "--all",
    "--no-mailmap",
    "--date=iso-strict",
    "--numstat",
    f"--format=format:{LOG_FORMAT}",
]


TRAILER_ARGV = [
    "log",
    "--all",
    "--no-mailmap",
    "--format=format:%x1e%H%x00%(trailers:only,unfold=true)",
]


def extract_repo(repo_id: str, repo_path: Path) -> tuple[list[Commit], dict]:
    result = run_git(repo_path, *LOG_ARGV)
    commits = _parse_log(repo_id, result.stdout)
    trailers = _parse_trailers(repo_path)
    for commit in commits:
        commit.trailers = trailers.get(commit.hash, "")
        if commit.is_merge:
            commit.patch_id = None
        else:
            commit.patch_id = _patch_id(repo_path, commit.hash)
    head_paths = _head_paths(repo_path)
    meta = {
        "repo_id": repo_id,
        "path": str(repo_path),
        "head_paths": head_paths,
        "readme_excerpt": _readme_excerpt(repo_path, head_paths),
        "tag_count": _tag_count(repo_path),
        "commit_count": len(commits),
    }
    return commits, meta


def extract_meta(input_path: Path) -> dict:
    return {
        "git_version": git_version(),
        "argv": ["git", "-C", "<repo>", *LOG_ARGV],
        "extracted_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "input_path": str(input_path.resolve()),
    }


def _parse_log(repo_id: str, stdout: str) -> list[Commit]:
    if not stdout:
        return []
    commits: list[Commit] = []
    for raw in stdout.split("\x1e"):
        if not raw.strip():
            continue
        lines = raw.splitlines()
        header = lines[0]
        fields = header.split("\x00")
        if len(fields) < 10:
            continue
        parents = [p for p in fields[2].split() if p]
        files = [_parse_numstat(line) for line in lines[1:] if line.strip()]
        files = [f for f in files if f is not None]
        adds, dels, net, churn, nfiles = volume_of(files)
        commits.append(
            Commit(
                repo_id=repo_id,
                hash=fields[0],
                tree=fields[1],
                parents=parents,
                is_merge=len(parents) > 1,
                author_name=fields[3],
                author_email=fields[4],
                author_date=fields[5],
                committer_name=fields[6],
                committer_email=fields[7],
                committer_date=fields[8],
                subject=fields[9],
                files=files,
                additions=adds,
                deletions=dels,
                net=net,
                churn=churn,
                files_changed=nfiles,
            )
        )
    return commits


def _parse_trailers(repo: Path) -> dict[str, str]:
    result = run_git(repo, *TRAILER_ARGV, check=False)
    if result.returncode != 0 or not result.stdout:
        return {}
    mapping: dict[str, str] = {}
    for raw in result.stdout.split("\x1e"):
        if not raw.strip():
            continue
        commit_hash, sep, rest = raw.partition("\x00")
        if sep:
            mapping[commit_hash.strip()] = rest.strip()
    return mapping


def _parse_numstat(line: str) -> FileChange | None:
    parts = line.split("\t", 2)
    if len(parts) < 3:
        return None
    adds_s, dels_s, path = parts
    is_binary = adds_s == "-" or dels_s == "-"
    if is_binary:
        return FileChange(path=path, additions=None, deletions=None, is_binary=True)
    try:
        return FileChange(
            path=path,
            additions=int(adds_s),
            deletions=int(dels_s),
            is_binary=False,
        )
    except ValueError:
        return FileChange(path=path, additions=None, deletions=None, is_binary=True)


def _patch_id(repo: Path, commit_hash: str) -> str | None:
    shown = run_git(repo, "show", "--format=", "--patch", commit_hash, check=False)
    if shown.returncode != 0 or not shown.stdout.strip():
        return None
    patched = run_git(None, "patch-id", "--stable", input_text=shown.stdout, check=False)
    if patched.returncode != 0 or not patched.stdout.strip():
        return None
    return patched.stdout.split()[0]


def _head_paths(repo: Path) -> list[str]:
    result = run_git(repo, "ls-tree", "-r", "--name-only", "HEAD", check=False)
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line]


def _readme_excerpt(repo: Path, head_paths: list[str]) -> str:
    names = {"README.md", "README", "README.rst", "README.txt"}
    candidates = [p for p in head_paths if p.split("/")[-1] in names]
    for name in candidates or ["README.md", "README"]:
        result = run_git(repo, "show", f"HEAD:{name}", check=False)
        if result.returncode == 0 and result.stdout:
            return result.stdout[:2000]
    return ""


def _tag_count(repo: Path) -> int:
    result = run_git(repo, "for-each-ref", "refs/tags", check=False)
    if result.returncode != 0:
        return 0
    return len([line for line in result.stdout.splitlines() if line])


def commits_as_dicts(commits: list[Commit]) -> list[dict]:
    return [to_dict(c) for c in commits]
