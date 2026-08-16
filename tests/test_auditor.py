from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from repoauditor.auditor.grok_cli import build_cmd, parse_headless_json
from repoauditor.auditor.prompt import SYSTEM_PROMPT, load_checklist
from repoauditor.auditor.run import cmd_analyze, cmd_pack
from repoauditor.auditor.validate import validate_report
from repoauditor.pipeline import cmd_scan
from tests.fixtures import spec


def test_checklist_is_a_background_check() -> None:
    ids = [item["id"] for item in load_checklist()]
    assert ids[0] == "purpose"
    assert "commit_substance" in ids
    assert "next_inspect" in ids
    assert "OPERATING PROTOCOL" in SYSTEM_PROMPT
    assert "Do not call tools" in SYSTEM_PROMPT
    assert "does not issue verdicts" in SYSTEM_PROMPT


def test_pack_contains_comment_docs_substance(department: Path, tmp_path: Path, as_of: date) -> None:
    out = tmp_path / "scan"
    cmd_scan(department, out, as_of)
    packs = cmd_pack(out)
    comment = next(p for p in packs if p["repo_id"] == "comment-docs")
    assert comment["readme"]["text"]
    assert "Apex Trading Engine" in comment["readme"]["text"]
    assert comment["checklist"]
    no_code = [
        c for c in comment["recent_commits"] if (c.get("substance") or {}).get("no_code")
    ]
    assert no_code
    assert comment["allowed_hashes"]
    dept = json.loads((out / "analysis" / "department_pack.json").read_text())
    assert dept["scope"] == "department"
    assert dept["repo_count"] == spec.REPO_COUNT


def test_validate_strips_invented_hashes() -> None:
    pack = {"repo_id": "x", "allowed_hashes": ["abc"]}
    report = {
        "purpose": "maybe",
        "category": "husk",
        "checklist": [
            {
                "id": "purpose",
                "answer": "x",
                "concern": True,
                "evidence_hashes": ["abc", "deadbeef"],
                "evidence_paths": ["README.md"],
            }
        ],
        "next_inspect": [{"hash": "nope", "why": "invented"}],
    }
    out = validate_report(report, pack)
    assert out["checklist"][0]["evidence_hashes"] == ["abc"]
    assert out["next_inspect"] == []
    assert "deadbeef" in out["stripped_unknown_hashes"]


def test_headless_grok_command_shape(tmp_path: Path) -> None:
    prompt = tmp_path / "p.md"
    prompt.write_text("hi", encoding="utf-8")
    cmd = build_cmd(
        grok_bin="/opt/grok",
        prompt_file=prompt,
        system_prompt="sys",
        cwd=tmp_path,
    )
    assert cmd[0] == "/opt/grok"
    assert "--prompt-file" in cmd
    assert "--json-schema" in cmd
    assert "--output-format" in cmd
    assert "--system-prompt-override" in cmd
    assert "--max-turns" in cmd
    assert cmd[cmd.index("--max-turns") + 1] == "1"
    assert "--disallowed-tools" in cmd
    assert "read_file" in cmd[cmd.index("--disallowed-tools") + 1]


def test_parse_headless_json_text() -> None:
    payload = {"purpose": "docs husk", "category": "husk", "checklist": [], "next_inspect": []}
    parsed = parse_headless_json(json.dumps({"text": json.dumps(payload)}))
    assert parsed["category"] == "husk"
    parsed2 = parse_headless_json(json.dumps({"structured_output": payload}))
    assert parsed2["purpose"] == "docs husk"


def test_analyze_uses_injected_runner(department: Path, tmp_path: Path, as_of: date) -> None:
    out = tmp_path / "scan"
    cmd_scan(department, out, as_of)

    def fake_run(cmd, **_kwargs):
        assert "--prompt-file" in cmd
        prompt = Path(cmd[cmd.index("--prompt-file") + 1])
        text = prompt.read_text(encoding="utf-8")
        if "executive summary" in text.lower() or '"scope": "department"' in text:
            report = {
                "headline": "dept",
                "executive_summary": "metrics plus interpretation",
                "run_the_business": [{"repo_id": "shared-ops", "why": "ops tree"}],
                "theater": [{"repo_id": "ai-demo", "why": "scaffold"}],
                "who_matters": [{"name": "Omar Ops", "why": "durable"}],
                "who_to_inspect": [{"name": "Quinn Hop", "why": "hop"}],
                "assistance": "cursor present",
                "unscriptable": [{"observation": "workflows empty", "evidence": "ci.yml"}],
                "open_next": ["shared-ops"],
            }
        else:
            assert "Checklist" in text
            report = {
                "purpose": "fixture",
                "category": "unknown",
                "checklist": [
                    {
                        "id": "purpose",
                        "answer": "from pack",
                        "concern": False,
                        "evidence_hashes": [],
                        "evidence_paths": [],
                    }
                ],
                "next_inspect": [],
            }
        return SimpleNamespace(returncode=0, stdout=json.dumps({"text": json.dumps(report)}), stderr="")

    reports = cmd_analyze(out, grok_bin="grok", runner=fake_run)
    assert len(reports) == spec.REPO_COUNT
    assert all(r["purpose"] == "fixture" for r in reports)
    index = json.loads((out / "analysis" / "index.json").read_text())
    assert len(index) == spec.REPO_COUNT
    executive = json.loads((out / "analysis" / "executive.json").read_text())
    assert executive["headline"] == "dept"
