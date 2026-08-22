from __future__ import annotations

from datetime import date
from pathlib import Path

from repoauditor.persist import read_json, write_json
from repoauditor.pipeline import _write_report, cmd_scan
from repoauditor.report.site import slug, write_report


def test_html_contains_caveat_and_hashes(department: Path, tmp_path: Path, as_of: date) -> None:
    out = tmp_path / "scan"
    cmd_scan(department, out, as_of)
    html = (out / "report" / "index.html").read_text(encoding="utf-8")
    findings = read_json(out / "derived" / "findings.json")
    people = read_json(out / "derived" / "people.json")
    repos = read_json(out / "derived" / "repos.json")
    for finding in findings:
        if finding.get("lens") != "repo":
            continue
        repo_page = out / "report" / "repos" / f"{slug(finding['subject_id'])}.html"
        page = repo_page.read_text(encoding="utf-8")
        assert finding["pattern"] in page
        for commit_hash in finding["evidence"]["commit_hashes"]:
            assert commit_hash in page
    assert "sensitive audit data" in html
    assert "additions" in html
    assert "class=\"sortable" in html
    assert "human contributors" in html
    assert "Git is not a timesheet" not in html
    assert 'data-col="shape"' not in html
    assert "col-bar" in html
    assert 'data-col="score"' in html
    assert ">score<" in html
    assert ">padding<" in html
    assert ">head substance<" in html
    assert 'data-col="t-padding"' in html
    assert "Click <strong>score</strong>" in html
    assert 'aria-sort="asc"' in html
    assert 'data-for="repos"' in html
    assert "Department executive" not in html
    js = (out / "report" / "assets" / "tables.js").read_text(encoding="utf-8")
    assert "heads().find" in js
    assert "heads.find(" not in js
    assert "Reset columns" in html
    assert "col-reset" in js
    repo_html = (out / "report" / "repos" / f"{slug(repos[0]['repo_id'])}.html").read_text()
    assert "heatmap-wrap" in repo_html
    assert ">unique paths<" in repo_html
    assert ">occupancy days<" in repo_html
    assert ">commits/day<" in repo_html
    assert ">Inspector tags<" in repo_html
    assert ">lines<" not in html.lower()
    human = next(p for p in people if not p.get("is_bot"))
    person_page = out / "report" / "people" / f"{slug(human['identity_key'])}.html"
    assert person_page.exists()
    person_html = person_page.read_text()
    assert ">durable<" in person_html
    assert ">occupancy days<" in person_html
    assert ">commits/day<" in person_html
    repo = repos[0]
    assert (out / "report" / "repos" / f"{slug(repo['repo_id'])}.html").exists()
    assert (out / "report" / "assets" / "tables.js").exists()
    assert repo.get("author_name") or repo.get("human_contributor_count") is not None
    assert "occupancy_days" in repo
    assert "activity_by_week" in repo


def test_write_report_survives_bool_checklist_answers(tmp_path: Path) -> None:
    as_of = date(2024, 7, 1)
    out = tmp_path / "scan"
    repos = [
        {
            "repo_id": "lab",
            "commit_count": 1,
            "human_contributor_count": 1,
            "churn": 0,
            "last_commit": "2024-01-01T00:00:00+00:00",
        }
    ]
    analysis = [
        {
            "repo_id": "lab",
            "purpose": True,
            "category": "docs",
            "headline": "kept",
            "executive_summary": "already done",
            "checklist": [
                {"id": "purpose", "answer": True, "concern": False},
                True,
                {"id": "padding", "answer": False, "concern": True},
            ],
            "next_inspect": [False, {"hash": "abc", "why": True}],
        }
    ]
    path = write_report(out, repos, [], [], as_of, str(tmp_path), analysis=analysis)
    html = path.read_text(encoding="utf-8")
    assert "lab" in html
    repo_page = (out / "report" / "repos" / f"{slug('lab')}.html").read_text(encoding="utf-8")
    assert "already done" in repo_page


def test_write_report_loads_per_repo_json(tmp_path: Path) -> None:
    as_of = date(2024, 7, 1)
    out = tmp_path / "scan"
    write_json(
        out / "derived" / "repos.json",
        [
            {
                "repo_id": "lab",
                "commit_count": 1,
                "human_contributor_count": 1,
                "churn": 0,
                "last_commit": "2024-01-01T00:00:00+00:00",
            }
        ],
    )
    write_json(out / "derived" / "people.json", [])
    write_json(out / "derived" / "findings.json", [])
    write_json(out / "derived" / "rankings.json", {})
    write_json(out / "raw" / "extract_meta.json", {"input_path": str(tmp_path)})
    write_json(
        out / "analysis" / "reports" / "lab.json",
        {
            "repo_id": "lab",
            "headline": "from disk",
            "executive_summary": "loaded without grok",
            "checklist": [{"id": "purpose", "answer": True, "concern": False}],
        },
    )
    write_json(
        out / "analysis" / "reports" / "lab.brief.json",
        {"repo_id": "should-ignore"},
    )
    path = _write_report(out, as_of, None)
    html = path.read_text(encoding="utf-8")
    assert "lab" in html
    repo_page = (out / "report" / "repos" / f"{slug('lab')}.html").read_text(encoding="utf-8")
    assert "loaded without grok" in repo_page
