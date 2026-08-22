"""Pack + headless Grok analyze stages."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable

from repoauditor.auditor.grok_cli import ANALYZE_TIMEOUT, EXPLORE_MAX_TURNS, GrokFailed, run_headless
from repoauditor.auditor.pack import _safe_name, brief_for_grok, build_department_pack, build_repo_pack
from repoauditor.auditor.prompt import (
    SCORER_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_SUBAGENTS,
    scorer_followup_prompt,
    user_prompt,
)
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
    json_schema: bool = False,
    model: str | None = None,
    subagents: bool = False,
    force: bool = False,
) -> list[dict]:
    paths = scan_paths(out_dir)
    if not paths["packs"].exists() or not any(paths["packs"].glob("*.json")):
        cmd_pack(out_dir)
    reports: list[dict] = []
    n_skip = 0
    n_run = 0
    analysis_dir = paths["analysis"]
    analysis_dir.mkdir(parents=True, exist_ok=True)
    pack_files = sorted(paths["packs"].glob("*.json"))
    for i, pack_path in enumerate(pack_files, start=1):
        pack = read_json(pack_path)
        dest = analysis_dir / f"{pack_path.stem}.json"
        kept = None if force else _load_finished_report(dest)
        if kept is not None:
            print(
                f"skip {i}/{len(pack_files)} {pack.get('repo_id')}",
                file=sys.stderr,
                flush=True,
            )
            reports.append(kept)
            n_skip += 1
            continue
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
                SYSTEM_PROMPT_SUBAGENTS if subagents else SYSTEM_PROMPT,
                Path(pack["path"]),
                grok_bin=grok_bin,
                runner=runner,
                timeout=timeout or ANALYZE_TIMEOUT,
                max_turns=max_turns or EXPLORE_MAX_TURNS,
                schema=None,
                explore=True,
                json_schema=json_schema,
                model=model,
                subagents=subagents,
            )
            validated = validate_report(raw, pack)
            if _needs_checklist(validated):
                scored = _score_followup(
                    analysis_dir / f"{pack_path.stem}.score.md",
                    validated,
                    pack,
                    grok_bin=grok_bin,
                    runner=runner,
                    timeout=timeout or ANALYZE_TIMEOUT,
                    json_schema=json_schema,
                    model=model,
                )
                if scored:
                    validated = _merge_scored(validated, scored, pack)
        except Exception as exc:
            stub = {
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
            validated = _keep_prior_report(dest, stub)
        write_json(dest, validated)
        reports.append(validated)
        n_run += 1
    write_json(paths["analysis_index"], reports)
    print(
        f"analyze finished: ran {n_run}, skipped {n_skip}, total {len(reports)}",
        file=sys.stderr,
        flush=True,
    )
    return reports


def _needs_checklist(report: dict) -> bool:
    return not any((item.get("answer") or "").strip() for item in report.get("checklist") or [])


def _score_followup(
    prompt_path: Path,
    report: dict,
    pack: dict,
    *,
    grok_bin: str | None,
    runner: Callable[..., Any] | None,
    timeout: int,
    json_schema: bool,
    model: str | None,
) -> dict | None:
    prompt_path.write_text(scorer_followup_prompt(report, pack), encoding="utf-8")
    try:
        raw = run_headless(
            prompt_path,
            SCORER_SYSTEM_PROMPT,
            Path(pack["path"]),
            grok_bin=grok_bin,
            runner=runner,
            timeout=timeout,
            max_turns=8,
            schema=None,
            explore=False,
            json_schema=json_schema,
            model=model,
        )
    except Exception:
        return None
    if _needs_checklist(raw if isinstance(raw, dict) else {}):
        return None
    return raw


def _merge_scored(base: dict, extra: dict, pack: dict) -> dict:
    scored = validate_report(extra, pack)
    if scored.get("checklist"):
        base["checklist"] = scored["checklist"]
    if scored.get("next_inspect"):
        base["next_inspect"] = scored["next_inspect"]
    if scored.get("purpose") and not base.get("purpose"):
        base["purpose"] = scored["purpose"]
    if scored.get("category") and scored.get("category") != "unknown":
        base["category"] = scored["category"]
    if scored.get("headline") and not base.get("headline"):
        base["headline"] = scored["headline"]
    return base


def _is_keeper(report: dict) -> bool:
    if not isinstance(report, dict):
        return False
    summary = report.get("executive_summary")
    if isinstance(summary, str) and summary.strip():
        return True
    for item in report.get("checklist") or []:
        if not isinstance(item, dict):
            continue
        answer = item.get("answer")
        if isinstance(answer, str) and answer.strip():
            return True
    return False


def unfinished_reports(out_dir: Path) -> list[dict]:
    """Packs with no finished inspector report (missing, empty, or error stub)."""
    paths = scan_paths(out_dir)
    packs_dir = paths["packs"]
    analysis_dir = paths["analysis"]
    if not packs_dir.exists():
        return []
    rows: list[dict] = []
    for pack_path in sorted(packs_dir.glob("*.json")):
        try:
            pack = read_json(pack_path)
        except (OSError, json.JSONDecodeError, ValueError):
            rows.append({"repo_id": pack_path.stem, "reason": "unreadable pack"})
            continue
        if not isinstance(pack, dict):
            rows.append({"repo_id": pack_path.stem, "reason": "unreadable pack"})
            continue
        repo_id = pack.get("repo_id") or pack_path.stem
        dest = analysis_dir / f"{pack_path.stem}.json"
        if _load_finished_report(dest) is not None:
            continue
        reason = "missing"
        if dest.exists():
            reason = "empty_or_stub"
        rows.append({"repo_id": repo_id, "reason": reason})
    return rows


def _load_finished_report(dest: Path) -> dict | None:
    if not dest.exists():
        return None
    try:
        prior = read_json(dest)
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    if isinstance(prior, dict) and _is_keeper(prior):
        return prior
    return None


def _keep_prior_report(dest: Path, stub: dict) -> dict:
    if not dest.exists():
        return stub
    try:
        prior = read_json(dest)
    except (OSError, json.JSONDecodeError, ValueError):
        return stub
    if not isinstance(prior, dict) or not _is_keeper(prior):
        return stub
    return prior


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
