from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def scan_paths(out_dir: Path) -> dict[str, Path]:
    return {
        "raw_repos": out_dir / "raw" / "repos.json",
        "raw_commits": out_dir / "raw" / "commits.jsonl",
        "extract_meta": out_dir / "raw" / "extract_meta.json",
        "identities": out_dir / "derived" / "identities.json",
        "suggestions": out_dir / "derived" / "identity_suggestions.json",
        "repos": out_dir / "derived" / "repos.json",
        "people": out_dir / "derived" / "people.json",
        "assistance": out_dir / "derived" / "assistance.json",
        "rankings": out_dir / "derived" / "rankings.json",
        "findings": out_dir / "derived" / "findings.json",
        "substance": out_dir / "derived" / "substance.json",
        "packs": out_dir / "analysis" / "packs",
        "analysis": out_dir / "analysis" / "reports",
        "analysis_index": out_dir / "analysis" / "index.json",
        "department_pack": out_dir / "analysis" / "department_pack.json",
        "executive": out_dir / "analysis" / "executive.json",
        "report": out_dir / "report" / "index.html",
    }
