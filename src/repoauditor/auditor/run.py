"""Pack + headless Grok analyze stages."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

from repoauditor.auditor.grok_cli import ANALYZE_TIMEOUT, EXPLORE_MAX_TURNS, GrokFailed, run_headless
from repoauditor.auditor.pack import _safe_name, brief_for_grok, build_department_pack, build_repo_pack
from repoauditor.auditor.prompt import SYSTEM_PROMPT, user_prompt
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
    for leftover in packs_dir.glob("*.json"):
        leftover.unlink()
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
    timeout: int = ANALYZE_TIMEOUT,
    max_turns: int = EXPLORE_MAX_TURNS,
) -> list[dict]:
    paths = scan_paths(out_dir)
    if not paths["packs"].exists() or not any(paths["packs"].glob("*.json")):
        cmd_pack(out_dir)
    reports: list[dict] = []
    analysis_dir = paths["analysis"]
    analysis_dir.mkdir(parents=True, exist_ok=True)
    pack_files = sorted(paths["packs"].glob("*.json"))
    for i, pack_path in enumerate(pack_files, start=1):
        pack = read_json(pack_path)
        print(
            f"analyze {i}/{len(pack_files)} {pack.get('repo_id')}",
            file=sys.stderr,
            flush=True,
        )
        brief_path = analysis_dir / f"{pack_path.stem}.brief.json"
        write_json(brief_path, brief_for_grok(pack))
        prompt_path = analysis_dir / f"{pack_path.stem}.prompt.md"
        prompt_path.write_text(
            user_prompt(pack, pack_path, brief_path=brief_path),
            encoding="utf-8",
        )
        try:
            raw = run_headless(
                prompt_path,
                SYSTEM_PROMPT,
                Path(pack["path"]),
                grok_bin=grok_bin,
                runner=runner,
                timeout=timeout or ANALYZE_TIMEOUT,
                max_turns=max_turns or EXPLORE_MAX_TURNS,
                schema=None,
                explore=True,
            )
            validated = validate_report(raw, pack)
        except Exception as exc:
            validated = {
                "repo_id": pack.get("repo_id"),
                "purpose": "",
                "category": "unknown",
                "headline": "",
                "executive_summary": "",
                "checklist": [],
                "next_inspect": [],
                "stripped_unknown_hashes": [],
                "analyze_error": _short_analyze_error(exc),
            }
        write_json(analysis_dir / f"{pack_path.stem}.json", validated)
        reports.append(validated)
    write_json(paths["analysis_index"], reports)
    return reports


def _short_analyze_error(exc: BaseException) -> str:
    if isinstance(exc, GrokFailed) and "timed out" in (exc.stderr or ""):
        return exc.stderr.strip()[:200]
    text = str(exc)
    lowered = text.lower()
    if "max turn" in lowered or "max_turns" in lowered:
        return "Analyze hit --max-turns (each tool call is a turn). Timeout does not add turns. Retry with a higher --max-turns."
    if "timed out" in text:
        return "Analyze timed out. Inspector ran too long; retry or raise --timeout."
    if text.startswith("Command '"):
        return "Analyze failed (grok exited). See analysis/reports/*.stderr.txt."
    return text[:400]
