from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from repoauditor.auditor.grok_cli import build_cmd, parse_headless_json
from repoauditor.auditor.prompt import SYSTEM_PROMPT, load_checklist, scorer_followup_prompt, user_prompt
from repoauditor.auditor.pack import brief_for_grok
from repoauditor.auditor.run import _keep_prior_report, cmd_analyze, cmd_pack
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
    assert "Mapper" in SYSTEM_PROMPT
    assert "Investigator" in SYSTEM_PROMPT
    assert "Scorer" in SYSTEM_PROMPT
    assert "JSON" in SYSTEM_PROMPT
    assert "catalog" in SYSTEM_PROMPT.lower()
    assert "spawn" not in SYSTEM_PROMPT.lower()
    assert "2–4" not in SYSTEM_PROMPT
    assert "one line" not in SYSTEM_PROMPT
    assert "meta-history" in SYSTEM_PROMPT
    assert "Do not wait for a follow-up" in SYSTEM_PROMPT
    assert "do not stop at the README" in SYSTEM_PROMPT
    assert "Ordinary readings" in SYSTEM_PROMPT
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


def test_validate_coerces_bool_answer() -> None:
    pack = {"repo_id": "x", "allowed_hashes": []}
    out = validate_report(
        {
            "purpose": "maybe",
            "category": "husk",
            "checklist": [
                {
                    "id": "purpose",
                    "answer": True,
                    "concern": False,
                    "evidence_hashes": [],
                    "evidence_paths": [],
                }
            ],
            "next_inspect": [],
        },
        pack,
    )
    assert out["checklist"][0]["answer"] == ""


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
    assert "--json-schema" not in cmd
    assert "--output-format" in cmd
    assert "--no-memory" in cmd
    with_schema = build_cmd(
        grok_bin="/opt/grok",
        prompt_file=relative,
        system_prompt="sys",
        cwd=repo,
        json_schema=True,
    )
    assert "--json-schema" in with_schema
    assert "--system-prompt-override" in cmd
    assert "--max-turns" in cmd
    assert cmd[cmd.index("--max-turns") + 1] == "512"
    cmd64 = build_cmd(
        grok_bin="/opt/grok",
        prompt_file=relative,
        system_prompt="sys",
        cwd=repo,
        max_turns=64,
    )
    assert cmd64[cmd64.index("--max-turns") + 1] == "64"
    named = build_cmd(
        grok_bin="/opt/grok",
        prompt_file=relative,
        system_prompt="sys",
        cwd=repo,
        model="muse-glimmer",
    )
    assert named[named.index("--model") + 1] == "muse-glimmer"
    denied = cmd[cmd.index("--disallowed-tools") + 1]
    assert "write" in denied
    assert "search_replace" in denied
    assert "read_file" not in denied
    assert "grep" not in denied
    assert "list_dir" not in denied
    assert "Agent" in denied
    assert "run_terminal_cmd" not in denied
    assert "--no-subagents" in cmd
    assert "--tools" in cmd
    tools = cmd[cmd.index("--tools") + 1]
    assert "read_file" in tools
    assert "Agent" not in tools
    kids = build_cmd(
        grok_bin="/opt/grok",
        prompt_file=relative,
        system_prompt="sys",
        cwd=repo,
        subagents=True,
    )
    assert "--no-subagents" not in kids
    assert "Agent" not in kids[kids.index("--disallowed-tools") + 1]
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
    assert "pack" in text
    assert str(pack_path.resolve()) in text
    assert str(brief_path.resolve()) in text
    assert "400" in text
    assert "hot_potato" in text
    assert "A then gap then B" in text
    assert hashes[10] not in text
    assert "diff xxx" not in text
    assert "f199.py" not in text
    assert "checklist[{id,answer,concern" in text
    assert len(text) < 2500


def test_scorer_followup_is_fill_in_only() -> None:
    text = scorer_followup_prompt(
        {
            "headline": "ASGS scripts still run",
            "executive_summary": "A coastal postprocess fork. Hash abcdef is cited.",
        },
        {"repo_id": "lab", "checklist": [{"id": "purpose"}, {"id": "padding"}]},
    )
    assert text.startswith("ONLY fill the JSON template")
    assert "Output the JSON object only" in text
    assert "copy the Notes block" in text
    assert "ASGS scripts still run" in text
    assert '"id": "purpose"' in text
    assert '"id": "padding"' in text


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


def test_parse_headless_json_prose_envelope() -> None:
    body = (
        "This checkout is a bag of coastal scripts, not a service.\n\n"
        "The README is still the StormSurgeLive operator card.\n"
    )
    parsed = parse_headless_json(json.dumps({"text": body, "stopReason": "end_turn"}))
    assert "coastal scripts" in parsed["executive_summary"]
    assert parsed["headline"].startswith("This checkout")
    parsed2 = parse_headless_json(body)
    assert "StormSurgeLive" in parsed2["executive_summary"]


def test_parse_headless_json_fenced_report() -> None:
    payload = {"purpose": "lab", "category": "script", "checklist": [], "next_inspect": []}
    blob = "Here you go:\n```json\n" + json.dumps(payload) + "\n```\n"
    parsed = parse_headless_json(json.dumps({"text": blob}))
    assert parsed["purpose"] == "lab"


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


def test_keep_prior_report_on_failed_parse(tmp_path: Path) -> None:
    dest = tmp_path / "repo.json"
    keeper = {
        "repo_id": "x",
        "headline": "kept",
        "executive_summary": "this write-up stays",
        "checklist": [{"id": "purpose", "answer": "lab", "concern": False}],
    }
    dest.write_text(json.dumps(keeper), encoding="utf-8")
    stub = {
        "repo_id": "x",
        "headline": "",
        "executive_summary": "",
        "checklist": [],
        "analyze_error": "could not parse JSON object from grok text",
    }
    kept = _keep_prior_report(dest, stub)
    assert kept["executive_summary"] == "this write-up stays"
    assert kept["headline"] == "kept"
    empty = tmp_path / "missing.json"
    assert _keep_prior_report(empty, stub)["analyze_error"]


def test_analyze_skips_keeper_reports_and_retries_stubs(tmp_path: Path) -> None:
    from repoauditor.persist import write_json

    repo = tmp_path / "repo"
    repo.mkdir()
    out = tmp_path / "scan"
    packs = out / "analysis" / "packs"
    packs.mkdir(parents=True)
    reports_dir = out / "analysis" / "reports"
    reports_dir.mkdir(parents=True)
    for repo_id in ("alpha", "bravo", "charlie"):
        write_json(
            packs / f"{repo_id}.json",
            {
                "repo_id": repo_id,
                "path": str(repo),
                "allowed_hashes": ["abc"],
                "checklist": load_checklist(),
            },
        )
    write_json(
        reports_dir / "alpha.json",
        {
            "repo_id": "alpha",
            "purpose": "done",
            "category": "docs",
            "headline": "kept",
            "executive_summary": "alpha already inspected",
            "checklist": [
                {
                    "id": "purpose",
                    "answer": "lab",
                    "concern": False,
                    "evidence_hashes": [],
                    "evidence_paths": [],
                }
            ],
            "next_inspect": [],
        },
    )
    write_json(
        reports_dir / "bravo.json",
        {
            "repo_id": "bravo",
            "purpose": "",
            "category": "unknown",
            "headline": "",
            "executive_summary": "",
            "checklist": [],
            "analyze_error": "killed mid-run",
        },
    )
    ran: list[str] = []

    def fake_run(cmd, **_kwargs):
        prompt = Path(cmd[cmd.index("--prompt-file") + 1])
        stem = prompt.name.removesuffix(".prompt.md")
        ran.append(stem)
        report = {
            "purpose": "fresh",
            "category": "unknown",
            "headline": stem,
            "executive_summary": f"{stem} new inspect",
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
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"text": json.dumps(report)}),
            stderr="",
        )

    reports = cmd_analyze(out, grok_bin="grok", runner=fake_run)
    assert ran == ["bravo", "charlie"]
    assert [row["repo_id"] for row in reports] == ["alpha", "bravo", "charlie"]
    assert reports[0]["executive_summary"] == "alpha already inspected"
    assert reports[1]["executive_summary"] == "bravo new inspect"
    assert reports[2]["executive_summary"] == "charlie new inspect"
    index = json.loads((out / "analysis" / "index.json").read_text())
    assert len(index) == 3


def test_analyze_retries_empty_report_files(tmp_path: Path) -> None:
    from repoauditor.persist import write_json

    repo = tmp_path / "repo"
    repo.mkdir()
    out = tmp_path / "scan"
    packs = out / "analysis" / "packs"
    packs.mkdir(parents=True)
    reports_dir = out / "analysis" / "reports"
    reports_dir.mkdir(parents=True)
    for repo_id in ("blank", "empty"):
        write_json(
            packs / f"{repo_id}.json",
            {
                "repo_id": repo_id,
                "path": str(repo),
                "allowed_hashes": ["abc"],
                "checklist": load_checklist(),
            },
        )
    (reports_dir / "blank.json").write_text("", encoding="utf-8")
    write_json(reports_dir / "empty.json", {})
    ran: list[str] = []

    def fake_run(cmd, **_kwargs):
        prompt = Path(cmd[cmd.index("--prompt-file") + 1])
        stem = prompt.name.removesuffix(".prompt.md")
        ran.append(stem)
        report = {
            "purpose": "fresh",
            "category": "unknown",
            "headline": stem,
            "executive_summary": f"{stem} new inspect",
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
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"text": json.dumps(report)}),
            stderr="",
        )

    reports = cmd_analyze(out, grok_bin="grok", runner=fake_run)
    assert ran == ["blank", "empty"]
    assert [row["executive_summary"] for row in reports] == [
        "blank new inspect",
        "empty new inspect",
    ]


def test_analyze_force_reruns_keepers(tmp_path: Path) -> None:
    from repoauditor.persist import write_json

    repo = tmp_path / "repo"
    repo.mkdir()
    out = tmp_path / "scan"
    packs = out / "analysis" / "packs"
    packs.mkdir(parents=True)
    reports_dir = out / "analysis" / "reports"
    reports_dir.mkdir(parents=True)
    write_json(
        packs / "alpha.json",
        {
            "repo_id": "alpha",
            "path": str(repo),
            "allowed_hashes": ["abc"],
            "checklist": load_checklist(),
        },
    )
    write_json(
        reports_dir / "alpha.json",
        {
            "repo_id": "alpha",
            "purpose": "done",
            "category": "docs",
            "headline": "kept",
            "executive_summary": "alpha already inspected",
            "checklist": [
                {
                    "id": "purpose",
                    "answer": "lab",
                    "concern": False,
                    "evidence_hashes": [],
                    "evidence_paths": [],
                }
            ],
            "next_inspect": [],
        },
    )
    ran: list[str] = []

    def fake_run(cmd, **_kwargs):
        prompt = Path(cmd[cmd.index("--prompt-file") + 1])
        ran.append(prompt.name.removesuffix(".prompt.md"))
        report = {
            "purpose": "fresh",
            "category": "unknown",
            "headline": "alpha",
            "executive_summary": "forced rerun",
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
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"text": json.dumps(report)}),
            stderr="",
        )

    reports = cmd_analyze(out, grok_bin="grok", runner=fake_run, force=True)
    assert ran == ["alpha"]
    assert reports[0]["executive_summary"] == "forced rerun"


def test_analyze_followup_fills_checklist(tmp_path: Path) -> None:
    from repoauditor.auditor.prompt import load_checklist
    from repoauditor.persist import write_json

    repo = tmp_path / "repo"
    repo.mkdir()
    out = tmp_path / "scan"
    packs = out / "analysis" / "packs"
    packs.mkdir(parents=True)
    write_json(
        packs / "lab.json",
        {
            "repo_id": "lab",
            "path": str(repo),
            "allowed_hashes": ["abc"],
            "checklist": load_checklist(),
        },
    )
    calls = {"n": 0}

    def fake_run(cmd, **_kwargs):
        calls["n"] += 1
        cwd = cmd[cmd.index("--cwd") + 1]
        assert Path(cwd) == repo
        prompt = Path(cmd[cmd.index("--prompt-file") + 1])
        if prompt.name.endswith(".score.md"):
            report = {
                "purpose": "lab notes",
                "category": "docs",
                "headline": "from scorer",
                "executive_summary": "",
                "checklist": [
                    {
                        "id": "purpose",
                        "answer": "notes only",
                        "concern": True,
                        "evidence_hashes": [],
                        "evidence_paths": ["README.md"],
                    }
                ],
                "next_inspect": [],
            }
            return SimpleNamespace(returncode=0, stdout=json.dumps({"text": json.dumps(report)}), stderr="")
        prose = (
            "This checkout is a lab notebook of coastal plots.\n\n"
            "The tree still has generateGraphs.py and a leftover README.\n"
        )
        return SimpleNamespace(returncode=0, stdout=json.dumps({"text": prose}), stderr="")

    reports = cmd_analyze(out, grok_bin="grok", runner=fake_run, json_schema=False)
    assert calls["n"] == 2
    assert reports[0]["executive_summary"].startswith("This checkout")
    assert reports[0]["checklist"][0]["id"] == "purpose"
    assert reports[0]["checklist"][0]["answer"] == "notes only"


def test_analyze_uses_injected_runner(department: Path, tmp_path: Path, as_of: date) -> None:
    out = tmp_path / "scan"
    cmd_scan(department, out, as_of)

    def fake_run(cmd, **_kwargs):
        assert "--prompt-file" in cmd
        prompt = Path(cmd[cmd.index("--prompt-file") + 1])
        assert prompt.is_absolute()
        text = prompt.read_text(encoding="utf-8")
        assert "pack " in text
        assert "brief " in text
        assert "ids " in text
        assert '"recent_commits"' not in text
        assert "--json-schema" not in cmd
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
