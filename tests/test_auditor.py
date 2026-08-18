from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from repoauditor.auditor.grok_cli import build_cmd, parse_headless_json
from repoauditor.auditor.prompt import SYSTEM_PROMPT, load_checklist, user_prompt
from repoauditor.auditor.pack import brief_for_grok
from repoauditor.auditor.run import cmd_analyze, cmd_pack
from repoauditor.auditor.validate import validate_report
from repoauditor.pipeline import cmd_scan
from tests.fixtures import spec


def test_checklist_is_a_background_check() -> None:
    items = load_checklist()
    ids = [item["id"] for item in items]
    assert ids[0] == "purpose"
    assert "commit_substance" in ids
    assert "next_inspect" in ids
    rtb = next(item for item in items if item["id"] == "run_the_business")
    assert "critical" in rtb["question"]
    assert "migration" in rtb["question"]
    assert "other teams depend" not in rtb["question"]
    gvb = next(item for item in items if item["id"] == "greenfield_vs_buy")
    assert "enterprise software" in gvb["question"]
    assert "Do not name vendors" in gvb["question"]
    assert "OPERATING PROTOCOL" in SYSTEM_PROMPT
    assert "Mapper" in SYSTEM_PROMPT
    assert "Investigator" in SYSTEM_PROMPT
    assert "Scorer" in SYSTEM_PROMPT
    assert "JSON only" in SYSTEM_PROMPT
    assert "catalog" in SYSTEM_PROMPT.lower()
    assert "2–4" not in SYSTEM_PROMPT
    assert "one line" not in SYSTEM_PROMPT
    assert "meta-history" in SYSTEM_PROMPT
    assert "No length cap" in SYSTEM_PROMPT
    assert "Do not restate the README" in SYSTEM_PROMPT
    assert "Do not stop at the README" in SYSTEM_PROMPT
    assert "Summary — last" in SYSTEM_PROMPT
    assert "Do not invent a second inspection" in SYSTEM_PROMPT
    assert "ordinary reading" in SYSTEM_PROMPT
    assert "tax auditor" not in SYSTEM_PROMPT


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
    assert out["checklist"][0]["id"] == "purpose"
    assert out["checklist"][0]["evidence_paths"] == ["README.md"]
    assert set(out["checklist"][0]) == {
        "id",
        "answer",
        "concern",
        "evidence_hashes",
        "evidence_paths",
    }
    assert out["next_inspect"] == []
    assert "deadbeef" in out["stripped_unknown_hashes"]


def test_headless_grok_command_shape(tmp_path: Path, monkeypatch) -> None:
    out = tmp_path / "scan2"
    prompt = out / "analysis" / "reports" / "repo.prompt.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text("hi", encoding="utf-8")
    repo = tmp_path / "the-repo"
    repo.mkdir()
    monkeypatch.chdir(tmp_path)
    relative = Path("scan2/analysis/reports/repo.prompt.md")
    assert not relative.is_absolute()
    cmd = build_cmd(
        grok_bin="/opt/grok",
        prompt_file=relative,
        system_prompt="sys",
        cwd=repo,
    )
    assert cmd[0] == "/opt/grok"
    assert "--prompt-file" in cmd
    prompt_arg = Path(cmd[cmd.index("--prompt-file") + 1])
    assert prompt_arg.is_absolute()
    assert prompt_arg == prompt.resolve()
    assert cmd[cmd.index("--cwd") + 1] == str(repo)
    assert "--json-schema" in cmd
    assert "--output-format" in cmd
    assert "--system-prompt-override" in cmd
    assert "--max-turns" in cmd
    assert cmd[cmd.index("--max-turns") + 1] == "48"
    cmd64 = build_cmd(
        grok_bin="/opt/grok",
        prompt_file=relative,
        system_prompt="sys",
        cwd=repo,
        max_turns=64,
    )
    assert cmd64[cmd64.index("--max-turns") + 1] == "64"
    denied = cmd[cmd.index("--disallowed-tools") + 1]
    assert "write" in denied
    assert "search_replace" in denied
    assert "read_file" not in denied
    assert "grep" not in denied
    assert "list_dir" not in denied
    assert "Agent" not in denied
    assert "run_terminal_cmd" not in denied
    assert "--no-subagents" not in cmd
    assert "--session-id" in cmd


def test_user_prompt_is_a_catalog(tmp_path: Path) -> None:
    pack_path = tmp_path / "big.json"
    brief_path = tmp_path / "big.brief.json"
    hashes = [f"{i:040d}" for i in range(400)]
    pack = {
        "repo_id": "big",
        "path": "/tmp/big",
        "metrics": {"commit_count": 4000, "churn": 99},
        "allowed_hashes": hashes,
        "head_paths": [f"f{i}.py" for i in range(200)],
        "recent_commits": [{"hash": hashes[0], "patch_excerpt": "diff " + ("x" * 2000)}],
        "deterministic_findings": [
            {
                "pattern": "hot_potato",
                "summary": "A then gap then B",
                "evidence": {"commit_hashes": hashes[:50]},
            }
        ],
        "checklist": [{"id": "purpose"}, {"id": "padding"}],
    }
    text = user_prompt(pack, pack_path, brief_path=brief_path)
    assert "catalog" in text.lower()
    assert str(pack_path.resolve()) in text
    assert str(brief_path.resolve()) in text
    assert "400" in text
    assert "hot_potato" in text
    assert "A then gap then B" in text
    assert hashes[10] not in text
    assert "diff xxx" not in text
    assert "f199.py" not in text
    assert len(text) < 4000


def test_brief_for_grok_drops_full_hash_dump() -> None:
    pack = {
        "repo_id": "x",
        "head_paths": [f"f{i}.py" for i in range(200)],
        "allowed_hashes": [f"{i:040d}" for i in range(200)],
        "recent_commits": [{"hash": "abc", "patch_excerpt": "x" * 5000}],
        "deterministic_findings": [
            {"pattern": "hot_potato", "summary": "gap", "evidence": {"commit_hashes": ["abc", "def"]}}
        ],
        "checklist": [],
    }
    brief = brief_for_grok(pack)
    assert brief["head_path_count"] == 200
    assert len(brief["head_path_sample"]) == 40
    assert "head_paths" not in brief
    assert len(brief["allowed_hashes"]) <= 40
    assert "abc" in brief["allowed_hashes"]
    assert len(brief["recent_commits"][0]["patch_excerpt"]) == 1200


def test_parse_headless_json_max_turns_without_report() -> None:
    from repoauditor.auditor.grok_cli import GrokFailed

    jammed = json.dumps({"stopReason": "max_turns", "text": "still mapping"})
    try:
        parse_headless_json(jammed)
    except GrokFailed as exc:
        assert "max turns" in (exc.stderr or "").lower()
    else:
        raise AssertionError("expected GrokFailed")


def test_parse_headless_json_text() -> None:
    payload = {"purpose": "docs husk", "category": "husk", "checklist": [], "next_inspect": []}
    parsed = parse_headless_json(json.dumps({"text": json.dumps(payload)}))
    assert parsed["category"] == "husk"
    parsed2 = parse_headless_json(json.dumps({"structured_output": payload}))
    assert parsed2["purpose"] == "docs husk"


def test_parse_headless_json_ignores_extra_objects() -> None:
    first = {"note": "mapper dump"}
    payload = {"purpose": "real", "category": "service", "checklist": [], "next_inspect": []}
    jammed = json.dumps({"text": json.dumps(first) + "\n" + json.dumps(payload)})
    parsed = parse_headless_json(jammed)
    assert parsed["purpose"] == "real"
    two_wrappers = json.dumps({"text": "{}"}) + "\n" + json.dumps({"structured_output": payload})
    parsed2 = parse_headless_json(two_wrappers)
    assert parsed2["category"] == "service"


def test_analyze_uses_injected_runner(department: Path, tmp_path: Path, as_of: date) -> None:
    out = tmp_path / "scan"
    cmd_scan(department, out, as_of)

    def fake_run(cmd, **_kwargs):
        assert "--prompt-file" in cmd
        prompt = Path(cmd[cmd.index("--prompt-file") + 1])
        assert prompt.is_absolute()
        text = prompt.read_text(encoding="utf-8")
        assert "catalog" in text.lower()
        assert "## Files" in text
        assert "## Counts" in text
        assert "allowed_hashes" in text
        assert '"recent_commits"' not in text
        report = {
            "purpose": "fixture",
            "category": "unknown",
            "headline": "fixture headline",
            "executive_summary": "one repo summary",
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
    assert all(r["checklist"][0]["id"] == "purpose" for r in reports)
    assert all(set(r["checklist"][0]) == {
        "id",
        "answer",
        "concern",
        "evidence_hashes",
        "evidence_paths",
    } for r in reports)
    index = json.loads((out / "analysis" / "index.json").read_text())
    assert len(index) == spec.REPO_COUNT
    assert all(r.get("executive_summary") == "one repo summary" for r in reports)
    assert not (out / "analysis" / "executive.json").exists()
