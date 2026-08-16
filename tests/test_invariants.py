from __future__ import annotations

from datetime import date
from pathlib import Path

from repoauditor.persist import read_json, read_jsonl
from repoauditor.pipeline import cmd_scan
from tests.fixtures import spec


def test_invariants(department: Path, tmp_path: Path, as_of: date) -> None:
    out = tmp_path / "scan"
    cmd_scan(department, out, as_of)
    findings = read_json(out / "derived" / "findings.json")
    commits = read_jsonl(out / "raw" / "commits.jsonl")
    identities = read_json(out / "derived" / "identities.json")
    suggestions = read_json(out / "derived" / "identity_suggestions.json")
    repos = read_json(out / "derived" / "repos.json")

    for finding in findings:
        assert finding["evidence"]["commit_hashes"], finding

    assert any(c["is_bot"] for c in commits)

    alias_ids = [
        i
        for i in identities
        if i["author_name"] == spec.ALIAS_NAME
    ]
    assert len(alias_ids) == 2
    applied = {i["identity_key"] for i in identities}
    # suggestions reference keys that still exist separately
    for suggestion in suggestions:
        for key in suggestion["identity_keys"]:
            assert key in applied

    for repo in repos:
        assert "lines" not in repo
        for field in ("additions", "deletions", "net", "churn", "files_changed"):
            assert field in repo
