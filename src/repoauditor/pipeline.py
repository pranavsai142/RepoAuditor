"""Orchestrate extract → assimilate → rank → flag → report. rank/flag do not call git."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from repoauditor.assimilate import assimilate
from repoauditor.assistants import assistance_inventory
from repoauditor.auditor.run import cmd_analyze, cmd_pack, cmd_substance, load_substance
from repoauditor.dates import parse_as_of
from repoauditor.discover import discover
from repoauditor.extract import commits_as_dicts, extract_meta, extract_repo
from repoauditor.identity import apply_bots_and_keys, build_identities
from repoauditor.patterns import detect_all
from repoauditor.persist import read_json, read_jsonl, scan_paths, write_json, write_jsonl
from repoauditor.rank import rank as rank_tables
from repoauditor.report import write_report


def cmd_discover(input_dir: Path) -> list[dict]:
    return discover(input_dir)


def cmd_extract(input_dir: Path, out_dir: Path) -> dict:
    repos = discover(input_dir)
    all_commits = []
    raw_repos = []
    for repo in repos:
        commits, meta = extract_repo(repo["repo_id"], Path(repo["path"]))
        raw_repos.append(meta)
        all_commits.extend(commits_as_dicts(commits))
    paths = scan_paths(out_dir)
    write_json(paths["raw_repos"], raw_repos)
    write_jsonl(paths["raw_commits"], all_commits)
    write_json(paths["extract_meta"], extract_meta(input_dir))
    return {"repos": len(raw_repos), "commits": len(all_commits), "out": str(out_dir)}


def _load_raw(out_dir: Path) -> tuple[list[dict], list[dict], dict]:
    paths = scan_paths(out_dir)
    return read_json(paths["raw_repos"]), read_jsonl(paths["raw_commits"]), read_json(paths["extract_meta"])


def cmd_assimilate(out_dir: Path) -> None:
    raw_repos, commits, _meta = _load_raw(out_dir)
    apply_bots_and_keys(commits)
    identities, suggestions = build_identities(commits)
    repos, people = assimilate(raw_repos, commits, identities)
    paths = scan_paths(out_dir)
    write_jsonl(paths["raw_commits"], commits)
    write_json(paths["identities"], identities)
    write_json(paths["suggestions"], suggestions)
    write_json(paths["repos"], repos)
    write_json(paths["people"], people)
    write_json(paths["assistance"], assistance_inventory(commits))


def cmd_rank(out_dir: Path, as_of: date | None = None) -> dict:
    del as_of  # rankings do not depend on as-of; flags do
    paths = scan_paths(out_dir)
    if not paths["repos"].exists():
        cmd_assimilate(out_dir)
    repos = read_json(paths["repos"])
    people = read_json(paths["people"])
    rankings = rank_tables(repos, people)
    write_json(paths["rankings"], rankings)
    return rankings


def cmd_flag(out_dir: Path, as_of: date) -> list[dict]:
    paths = scan_paths(out_dir)
    if not paths["repos"].exists():
        cmd_assimilate(out_dir)
    if not paths["substance"].exists():
        cmd_substance(out_dir)
    repos = read_json(paths["repos"])
    people = read_json(paths["people"])
    commits = read_jsonl(paths["raw_commits"])
    findings = detect_all(repos, people, commits, as_of, load_substance(out_dir))
    write_json(paths["findings"], findings)
    return findings


def _write_report(out_dir: Path, as_of: date, analysis: list[dict] | None = None) -> Path:
    paths = scan_paths(out_dir)
    repos = read_json(paths["repos"])
    people = read_json(paths["people"])
    rankings = read_json(paths["rankings"]) if paths["rankings"].exists() else {}
    findings = read_json(paths["findings"]) if paths["findings"].exists() else []
    meta = read_json(paths["extract_meta"])
    if analysis is None and paths["analysis_index"].exists():
        analysis = read_json(paths["analysis_index"])
    assistance = read_json(paths["assistance"]) if paths["assistance"].exists() else {}
    executive = read_json(paths["executive"]) if paths["executive"].exists() else None
    return write_report(
        out_dir,
        repos,
        people,
        findings,
        as_of,
        meta["input_path"],
        analysis=analysis or [],
        assistance=assistance,
        executive=executive,
        rankings=rankings,
    )


def cmd_scan(
    input_dir: Path,
    out_dir: Path,
    as_of: date,
    *,
    analyze: bool = False,
    grok_bin: str | None = None,
) -> dict:
    extract_info = cmd_extract(input_dir, out_dir)
    cmd_assimilate(out_dir)
    cmd_substance(out_dir)
    rankings = cmd_rank(out_dir, as_of)
    del rankings
    findings = cmd_flag(out_dir, as_of)
    cmd_pack(out_dir)
    analysis: list[dict] = []
    report = _write_report(out_dir, as_of, analysis)
    if analyze:
        analysis = cmd_analyze(out_dir, grok_bin=grok_bin)
        report = _write_report(out_dir, as_of, analysis)
    return {
        **extract_info,
        "findings": len(findings),
        "packs": len(list((out_dir / "analysis" / "packs").glob("*.json"))),
        "analyzed": len(analysis),
        "as_of": as_of.isoformat(),
        "report": str(report),
    }


def parse_as_of_arg(value: str | None) -> date:
    if value:
        return parse_as_of(value)
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).date()
