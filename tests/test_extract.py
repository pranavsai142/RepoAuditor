from __future__ import annotations

from pathlib import Path

from repoauditor.discover import discover
from repoauditor.extract import LOG_ARGV, extract_repo
from repoauditor.gitcmd import run_git


def _oracle_count(repo: Path) -> int:
    result = run_git(repo, "rev-list", "--all", "--count")
    return int(result.stdout.strip() or "0")


def _oracle_numstat_sum(repo: Path) -> tuple[int, int]:
    result = run_git(repo, *LOG_ARGV)
    adds = 0
    dels = 0
    current_merge = False
    for raw in result.stdout.split("\x1e"):
        if not raw.strip():
            continue
        lines = raw.splitlines()
        fields = lines[0].split("\x00")
        parents = fields[2].split() if len(fields) > 2 else []
        current_merge = len(parents) > 1
        if current_merge:
            continue
        for line in lines[1:]:
            parts = line.split("\t", 2)
            if len(parts) < 3 or parts[0] == "-" or parts[1] == "-":
                continue
            adds += int(parts[0])
            dels += int(parts[1])
    return adds, dels


def test_extract_matches_git_oracle(department: Path) -> None:
    for repo in discover(department):
        path = Path(repo["path"])
        commits, meta = extract_repo(repo["repo_id"], path)
        assert len(commits) == _oracle_count(path), repo["repo_id"]
        assert meta["commit_count"] == len(commits)
        vol_adds = sum(c.additions or 0 for c in commits if not c.is_merge and c.additions is not None)
        vol_dels = sum(c.deletions or 0 for c in commits if not c.is_merge and c.deletions is not None)
        o_adds, o_dels = _oracle_numstat_sum(path)
        assert vol_adds == o_adds, repo["repo_id"]
        assert vol_dels == o_dels, repo["repo_id"]
        for commit in commits:
            assert commit.author_name
            assert commit.author_email
            assert commit.author_date
            assert commit.committer_name
            assert commit.tree
            assert commit.hash
            if commit.is_merge:
                assert commit.patch_id is None


def test_extract_meta_records_argv(department: Path) -> None:
    from repoauditor.extract import extract_meta

    meta = extract_meta(department)
    assert "git version" in meta["git_version"]
    assert "--all" in meta["argv"]
    assert "--numstat" in meta["argv"]
    assert "--no-mailmap" in meta["argv"]
