from __future__ import annotations

from collections import defaultdict
from datetime import date
from pathlib import Path

from repoauditor.pipeline import cmd_flag, cmd_scan
from tests.fixtures import spec


def _findings_by_repo(findings: list[dict]) -> dict[str, set[str]]:
    by: dict[str, set[str]] = defaultdict(set)
    for finding in findings:
        if finding["lens"] == "repo":
            by[finding["subject_id"]].add(finding["pattern"])
    return by


def test_founding_patterns_on_fixtures(department: Path, tmp_path: Path, as_of: date) -> None:
    out = tmp_path / "scan"
    cmd_scan(department, out, as_of)
    findings = cmd_flag(out, as_of)
    by_repo = _findings_by_repo(findings)
    for repo_id, expected in spec.REQUIRED_FLAGS.items():
        assert expected <= by_repo[repo_id], (repo_id, by_repo[repo_id])
    assert spec.HEALTHY not in by_repo or by_repo[spec.HEALTHY] == set()

    for pattern, name in spec.REQUIRED_PERSON_FLAGS.items():
        hits = [f for f in findings if f["pattern"] == pattern]
        assert hits, pattern
        assert any(name in f["subject_id"] for f in hits)
    for finding in findings:
        assert finding["evidence"]["commit_hashes"]
    shared = [f for f in findings if f["subject_id"] == "shared-ops"]
    assert shared == []


def test_healthy_has_no_founding_flags(department: Path, tmp_path: Path, as_of: date) -> None:
    out = tmp_path / "scan"
    cmd_scan(department, out, as_of)
    findings = [f for f in cmd_flag(out, as_of) if f["subject_id"] == spec.HEALTHY]
    assert findings == []
