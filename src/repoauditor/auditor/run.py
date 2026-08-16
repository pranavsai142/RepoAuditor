"""Pack + headless Grok analyze stages."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from repoauditor.auditor.grok_cli import run_headless
from repoauditor.auditor.pack import _safe_name, build_department_pack, build_repo_pack
from repoauditor.auditor.prompt import EXECUTIVE_SYSTEM_PROMPT, SYSTEM_PROMPT, executive_prompt, user_prompt
from repoauditor.auditor.schema import EXECUTIVE_JSON_SCHEMA
from repoauditor.auditor.substance import score_repo
from repoauditor.auditor.validate import validate_report
from repoauditor.persist import read_json, read_jsonl, scan_paths, write_json


def cmd_substance(out_dir: Path, limit: int = 500) -> dict[str, dict]:
    paths = scan_paths(out_dir)
    raw_repos = {r["repo_id"]: r for r in read_json(paths["raw_repos"])}
    commits = read_jsonl(paths["raw_commits"])
    by_repo: dict[str, list[dict]] = {}
    for commit in commits:
        by_repo.setdefault(commit["repo_id"], []).append(commit)
    merged: dict[str, dict] = {}
    for repo_id, rows in by_repo.items():
        raw = raw_repos.get(repo_id) or {}
        repo_path = Path(raw.get("path") or "")
        if not repo_path.exists():
            continue
        merged.update(score_repo(repo_path, rows, limit=limit))
    write_json(paths["substance"], list(merged.values()))
    return merged


def load_substance(out_dir: Path) -> dict[str, dict]:
    paths = scan_paths(out_dir)
    if not paths["substance"].exists():
        return {}
    rows = read_json(paths["substance"])
    return {f"{row['repo_id']}:{row['hash']}": row for row in rows}


def cmd_pack(out_dir: Path) -> list[dict]:
    paths = scan_paths(out_dir)
    repos = read_json(paths["repos"])
    commits = read_jsonl(paths["raw_commits"])
    findings = read_json(paths["findings"]) if paths["findings"].exists() else []
    substance = load_substance(out_dir)
    packs_dir = paths["packs"]
    packs_dir.mkdir(parents=True, exist_ok=True)
    packs = []
    for repo in repos:
        pack = build_repo_pack(repo, commits, findings, substance, Path(repo["path"]))
        dest = packs_dir / f"{_safe_name(repo['repo_id'])}.json"
        write_json(dest, pack)
        packs.append(pack)
    paths_meta = paths
    rankings = read_json(paths_meta["rankings"]) if paths_meta["rankings"].exists() else {}
    people = read_json(paths_meta["people"]) if paths_meta["people"].exists() else []
    assistance = read_json(paths_meta["assistance"]) if paths_meta["assistance"].exists() else {}
    meta = read_json(paths_meta["extract_meta"]) if paths_meta["extract_meta"].exists() else {}
    dept = build_department_pack(
        repos,
        people,
        findings,
        rankings,
        assistance,
        meta.get("input_path") or "",
        "",
    )
    write_json(paths_meta["department_pack"], dept)
    return packs


def cmd_analyze(
    out_dir: Path,
    *,
    grok_bin: str | None = None,
    runner: Callable[..., Any] | None = None,
    timeout: int = 180,
) -> list[dict]:
    paths = scan_paths(out_dir)
    if not paths["packs"].exists() or not any(paths["packs"].glob("*.json")):
        cmd_pack(out_dir)
    reports: list[dict] = []
    analysis_dir = paths["analysis"]
    analysis_dir.mkdir(parents=True, exist_ok=True)
    for pack_path in sorted(paths["packs"].glob("*.json")):
        pack = read_json(pack_path)
        prompt_path = analysis_dir / f"{pack_path.stem}.prompt.md"
        prompt_path.write_text(user_prompt(pack), encoding="utf-8")
        raw = run_headless(
            prompt_path,
            SYSTEM_PROMPT,
            Path(pack["path"]),
            grok_bin=grok_bin,
            runner=runner,
            timeout=timeout,
            schema=None,
        )
        validated = validate_report(raw, pack)
        write_json(analysis_dir / f"{pack_path.stem}.json", validated)
        reports.append(validated)
    if paths["department_pack"].exists():
        dept = read_json(paths["department_pack"])
        exec_prompt = analysis_dir / "department.prompt.md"
        exec_prompt.write_text(executive_prompt(dept), encoding="utf-8")
        cwd = Path(dept.get("input_path") or out_dir)
        if not cwd.exists():
            cwd = out_dir
        executive = run_headless(
            exec_prompt,
            EXECUTIVE_SYSTEM_PROMPT,
            cwd,
            grok_bin=grok_bin,
            runner=runner,
            timeout=timeout,
            schema=EXECUTIVE_JSON_SCHEMA,
        )
        write_json(paths["executive"], executive)
    write_json(paths["analysis_index"], reports)
    return reports
