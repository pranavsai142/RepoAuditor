from __future__ import annotations

from pathlib import Path

from repoauditor.pipeline import cmd_extract, cmd_rank
from tests.fixtures.spec import AS_OF


def test_rank_axes_and_no_lines_field(department: Path, tmp_path: Path) -> None:
    out = tmp_path / "scan"
    cmd_extract(department, out)
    rankings = cmd_rank(out)

    def walk(obj, trail=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                assert key != "lines", trail
                walk(value, f"{trail}.{key}")
        elif isinstance(obj, list):
            for item in obj:
                walk(item, trail)

    walk(rankings)
    assert set(rankings["repos"]) == {"by_last_commit", "by_churn", "by_human_contributors"}
    assert "by_durable_repos" in rankings["people"]
    last = rankings["repos"]["by_last_commit"]
    assert last.index("burst-graveyard") < last.index("healthy-team")
    from repoauditor.persist import read_json

    repos = {r["repo_id"]: r for r in read_json(out / "derived" / "repos.json")}
    assert repos["one-person-island"]["human_contributor_count"] == 1
    assert "lines" not in repos["healthy-team"]
    assert {"additions", "deletions", "net", "churn", "files_changed"} <= set(repos["healthy-team"])


def test_rank_does_not_need_git(department: Path, tmp_path: Path, monkeypatch) -> None:
    out = tmp_path / "scan"
    cmd_extract(department, out)
    cmd_rank(out)

    def boom(*_a, **_k):
        raise AssertionError("git must not be called during rank")

    monkeypatch.setattr("repoauditor.gitcmd.run_git", boom)
    cmd_rank(out)
