from __future__ import annotations

from datetime import date
from pathlib import Path

from repoauditor import CAVEAT
from repoauditor.persist import read_json
from repoauditor.pipeline import cmd_scan


def test_html_contains_caveat_and_hashes(department: Path, tmp_path: Path, as_of: date) -> None:
    out = tmp_path / "scan"
    cmd_scan(department, out, as_of)
    html = (out / "report" / "index.html").read_text(encoding="utf-8")
    assert CAVEAT in html
    findings = read_json(out / "derived" / "findings.json")
    html_patterns = set()
    for finding in findings:
        assert finding["pattern"] in html
        html_patterns.add(finding["pattern"])
        for commit_hash in finding["evidence"]["commit_hashes"]:
            assert commit_hash in html
    assert html_patterns == {f["pattern"] for f in findings}
    assert "sensitive audit data" in html
    assert "additions" in html
    assert ">lines<" not in html.lower()
