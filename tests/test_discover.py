from __future__ import annotations

from pathlib import Path

from repoauditor.discover import discover
from tests.fixtures import spec


def test_discover_finds_all_fixture_repos(department: Path) -> None:
    found = discover(department)
    ids = sorted(r["repo_id"] for r in found)
    assert ids == sorted(spec.REPOS)
    assert len(found) == spec.REPO_COUNT
    nested = next(r for r in found if r["repo_id"] == "nested/deep/nested-husk")
    assert (Path(nested["path"]) / ".git").exists()


def test_single_repo_department(tmp_path: Path) -> None:
    from tests.fixtures.build_fixtures import build_readme_husk

    build_readme_husk(tmp_path / "only")
    only = tmp_path / "only"
    found = discover(only)
    assert [r["repo_id"] for r in found] == ["only"]
    assert found[0]["path"] == str(only.resolve())


def test_targeted_repo_ignores_nested_git(tmp_path: Path) -> None:
    from tests.fixtures.build_fixtures import build_readme_husk

    parent = tmp_path / "support"
    build_readme_husk(parent)
    build_readme_husk(parent / "thesis")
    found = discover(parent)
    assert [r["repo_id"] for r in found] == ["support"]
    assert (parent / "thesis" / ".git").exists()


def test_folder_of_repos_still_walks(department: Path) -> None:
    assert not (department / ".git").exists()
    found = discover(department)
    assert "nested/deep/nested-husk" in {r["repo_id"] for r in found}
