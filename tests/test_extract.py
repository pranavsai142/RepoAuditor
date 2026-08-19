from __future__ import annotations

import os
import subprocess
from datetime import date
from pathlib import Path

import pytest

from repoauditor.auditor.substance import score_repo, show_patch
from repoauditor.discover import discover
from repoauditor.extract import LOG_ARGV, extract_repo
from repoauditor.gitcmd import run_git


def _init_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    subprocess.run(
        ["git", "-c", "init.defaultBranch=main", "init"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    for key, value in (
        ("user.name", "fixture"),
        ("user.email", "fixture@dept.test"),
        ("commit.gpgsign", "false"),
    ):
        subprocess.run(["git", "config", key, value], cwd=path, check=True, capture_output=True)
    return path


def _commit_bytes(repo: Path, rel: str, payload: bytes, message: str) -> None:
    dest = repo / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(payload)
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Latin Author",
            "GIT_AUTHOR_EMAIL": "latin@dept.test",
            "GIT_AUTHOR_DATE": "2024-03-01T12:00:00+00:00",
            "GIT_COMMITTER_NAME": "Latin Author",
            "GIT_COMMITTER_EMAIL": "latin@dept.test",
            "GIT_COMMITTER_DATE": "2024-03-01T12:00:00+00:00",
        }
    )
    subprocess.run(["git", "add", rel], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", message], cwd=repo, check=True, capture_output=True, env=env)


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


def test_extract_survives_non_utf8_patch(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "latin1")
    # 0xc3 with no continuation byte — the crash from a real department clone.
    _commit_bytes(repo, "note.txt", b"caf\xe9 \xc3 broken\n", "add latin-1 note")
    commits, meta = extract_repo("latin1", repo)
    assert len(commits) == 1
    assert meta["commit_count"] == 1
    assert commits[0].hash
    assert commits[0].patch_id  # raw bytes still hash
    show_patch(repo, commits[0].hash)  # substance path must not raise either
    scored = score_repo(repo, [{"repo_id": "latin1", "hash": commits[0].hash, "is_merge": False}])
    assert f"latin1:{commits[0].hash}" in scored


def test_extract_since_drops_older_commits(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "fork")
    _commit_bytes(repo, "upstream.txt", b"old\n", "upstream")
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Org Dev",
            "GIT_AUTHOR_EMAIL": "dev@dept.test",
            "GIT_AUTHOR_DATE": "2024-06-15T12:00:00+00:00",
            "GIT_COMMITTER_NAME": "Org Dev",
            "GIT_COMMITTER_EMAIL": "dev@dept.test",
            "GIT_COMMITTER_DATE": "2024-06-15T12:00:00+00:00",
        }
    )
    (repo / "org.txt").write_text("new\n", encoding="utf-8")
    subprocess.run(["git", "add", "org.txt"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "org work"], cwd=repo, check=True, capture_output=True, env=env)
    all_commits, _ = extract_repo("fork", repo)
    assert len(all_commits) == 2
    cut, _ = extract_repo("fork", repo, since=date(2024, 6, 1))
    assert len(cut) == 1
    assert cut[0].subject == "org work"


def test_run_git_ignores_inherited_git_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = _init_repo(tmp_path / "target")
    _commit_bytes(target, "keep.txt", b"only in target\n", "target commit")
    decoy = _init_repo(tmp_path / "decoy")
    _commit_bytes(decoy, "other.txt", b"decoy\n", "decoy commit")
    monkeypatch.setenv("GIT_DIR", str(decoy / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(decoy))
    result = run_git(target, "ls-tree", "-r", "--name-only", "HEAD")
    assert "keep.txt" in result.stdout
    assert "other.txt" not in result.stdout
