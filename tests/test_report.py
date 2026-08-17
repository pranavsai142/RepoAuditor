from __future__ import annotations

from datetime import date
from pathlib import Path

from repoauditor.persist import read_json
from repoauditor.pipeline import cmd_scan
from repoauditor.report.site import slug


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
