from __future__ import annotations

from datetime import date
from pathlib import Path

from repoauditor.assistants import classify_assistants
from repoauditor.persist import read_json
from repoauditor.pipeline import cmd_scan


def test_cursor_trailer_is_assistance() -> None:
    hits = classify_assistants(
        {
            "author_name": "Pat Prompt",
            "author_email": "pat@dept.test",
            "committer_name": "Pat Prompt",
            "committer_email": "pat@dept.test",
            "subject": "init",
            "trailers": "Co-authored-by: Cursor <cursoragent@cursor.com>",
        }
    )
    assert any(h["id"] == "cursor" for h in hits)


def test_inventory_and_durable_people(department: Path, tmp_path: Path, as_of: date) -> None:
    out = tmp_path / "scan"
    cmd_scan(department, out, as_of)
    assistance = read_json(out / "derived" / "assistance.json")
    ids = {a["id"] for a in assistance["assistants"]}
    assert "cursor" in ids
    assert assistance["ai_assisted_commits"] >= 6
    repos = {r["repo_id"]: r for r in read_json(out / "derived" / "repos.json")}
    assert repos["shared-ops"]["is_ops"] is True
    assert repos["requirements-week"]["has_requirements"] is True
    people = read_json(out / "derived" / "people.json")
    omar = next(p for p in people if p["author_name"] == "Omar Ops")
    quinn = next(p for p in people if p["author_name"] == "Quinn Hop")
    assert omar["durable_repo_count"] >= 1
    assert quinn["thin_repo_count"] >= 3
    assert omar["durable_repo_count"] > quinn["durable_repo_count"]
