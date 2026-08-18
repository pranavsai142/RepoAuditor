"""Invoke Grok Build in headless mode (`grok --prompt-file`)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Callable

from repoauditor.auditor.schema import AUDITOR_JSON_SCHEMA

# Investigate the repo. Only block mutations. Web is off via --disable-web-search.
# Each parent tool call is a turn. Keep these high so a fat repo can finish.
EXPLORE_MAX_TURNS = 512
EXEC_MAX_TURNS = 1
ANALYZE_TIMEOUT = 86400
DISALLOWED_TOOLS = "search_replace,write"
EXEC_DISALLOWED_TOOLS = "search_replace,write,Agent"


class GrokNotFound(RuntimeError):
    pass


class GrokFailed(RuntimeError):
    def __init__(self, cmd: list[str], returncode: int, stderr: str, stdout: str):
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr
        self.stdout = stdout
        super().__init__(
            f"headless grok failed ({returncode}): {(stderr or stdout or '').strip()[:1500] or 'no output'}"
        )


def find_grok(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    env = os.environ.get("GROK_BIN")
    if env:
        return env
    found = shutil.which("grok")
    if found:
        return found
    home = Path.home() / ".grok" / "bin" / "grok"
    if home.exists():
        return str(home)
    raise GrokNotFound(
        "grok CLI not found. Install Grok Build or set GROK_BIN. "
        "Headless analyze runs `grok --prompt-file` (see grok --help)."
    )


def build_cmd(
    *,
    grok_bin: str,
    prompt_file: Path,
    system_prompt: str,
    cwd: Path,
    schema: dict | None = None,
    explore: bool = True,
    max_turns: int | None = None,
) -> list[str]:
    schema = schema or AUDITOR_JSON_SCHEMA
    # grok opens --prompt-file relative to --cwd (the scanned repo), not process cwd
    prompt = Path(prompt_file).expanduser().resolve()
    # Fresh session id so a TUI `--resume` of an older live run cannot attach
    # to this process (sessions are grouped by --cwd).
    session_id = str(uuid.uuid4())
    turns = max_turns if max_turns is not None else (EXPLORE_MAX_TURNS if explore else EXEC_MAX_TURNS)
    cmd = [
        grok_bin,
        "--prompt-file",
        str(prompt),
        "--session-id",
        session_id,
        "--json-schema",
        json.dumps(schema, separators=(",", ":")),
        "--output-format",
        "json",
        "--system-prompt-override",
        system_prompt,
        "--cwd",
        str(cwd),
        "--disable-web-search",
        "--no-auto-update",
        "--verbatim",
        "--yolo",
        "--no-plan",
    ]
    if explore:
        cmd.extend(
            [
                "--disallowed-tools",
                DISALLOWED_TOOLS,
                "--max-turns",
                str(turns),
            ]
        )
    else:
        cmd.extend(
            [
                "--disallowed-tools",
                EXEC_DISALLOWED_TOOLS,
                "--max-turns",
                str(turns),
                "--no-subagents",
            ]
        )
    return cmd


def parse_headless_json(raw: str) -> dict:
    """Accept a grok wrapper, raw auditor JSON, or several objects jammed together."""
    if not raw or not raw.strip():
        raise ValueError("headless grok produced empty stdout")
    candidates = _iter_json_dicts(raw)
    picked = _pick_report_dict(candidates)
    if picked is None:
        raise ValueError("headless grok JSON had no object")
    if picked.get("type") == "error":
        raise GrokFailed(["grok"], 1, picked.get("message") or raw, raw)
    reason = str(picked.get("stopReason") or picked.get("stop_reason") or "")
    if "max_turn" in reason.lower() or reason.lower() == "max_turns":
        if not _looks_like_report(picked) and not picked.get("structured_output") and not (
            isinstance(picked.get("text"), str) and picked.get("text", "").strip().startswith("{")
        ):
            raise GrokFailed(["grok"], 1, "max turns reached", raw)
    if picked.get("structured_output"):
        out = picked["structured_output"]
        if isinstance(out, dict):
            return out
        if isinstance(out, str):
            nested = _pick_report_dict(_iter_json_dicts(out))
            if nested:
                return nested
    text = picked.get("text")
    if isinstance(text, dict):
        return text
    if isinstance(text, str) and text.strip():
        nested = _pick_report_dict(_iter_json_dicts(text))
        if nested:
            return nested
        return _parse_json_object(text)
    if _looks_like_report(picked):
        return picked
    raise ValueError("headless grok JSON had no structured_output or text")


def _iter_json_dicts(text: str) -> list[dict]:
    decoder = json.JSONDecoder()
    found: list[dict] = []
    idx = 0
    n = len(text)
    while idx < n:
        while idx < n and text[idx] not in "{[":
            idx += 1
        if idx >= n:
            break
        try:
            value, end = decoder.raw_decode(text, idx)
        except json.JSONDecodeError:
            idx += 1
            continue
        if isinstance(value, dict):
            found.append(value)
        elif isinstance(value, list):
            found.extend(item for item in value if isinstance(item, dict))
        idx = max(end, idx + 1)
    return found


def _looks_like_report(data: dict) -> bool:
    return "checklist" in data or ("purpose" in data and "category" in data) or "headline" in data


def _pick_report_dict(candidates: list[dict]) -> dict | None:
    if not candidates:
        return None
    for item in reversed(candidates):
        if _looks_like_report(item):
            return item
    for item in reversed(candidates):
        if item.get("structured_output") or item.get("text") is not None:
            return item
    return candidates[-1]


def _parse_json_object(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    picked = _pick_report_dict(_iter_json_dicts(text))
    if picked:
        return picked
    raise ValueError("could not parse JSON object from grok text")


def run_headless(
    prompt_file: Path,
    system_prompt: str,
    cwd: Path,
    *,
    grok_bin: str | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    timeout: int = 90,
    schema: dict | None = None,
    explore: bool = True,
    max_turns: int | None = None,
) -> dict:
    binary = find_grok(grok_bin)
    cmd = build_cmd(
        grok_bin=binary,
        prompt_file=prompt_file,
        system_prompt=system_prompt,
        cwd=cwd,
        schema=schema,
        explore=explore,
        max_turns=max_turns,
    )
    run = runner or subprocess.run
    limit = timeout or 90
    try:
        result = run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=limit,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        _stash_output(prompt_file, stdout, stderr)
        raise GrokFailed(cmd, -1, f"timed out after {limit}s", stdout) from exc
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    if result.returncode != 0:
        _stash_output(prompt_file, stdout, stderr)
        raise GrokFailed(cmd, result.returncode, stderr, stdout)
    try:
        return parse_headless_json(stdout)
    except (ValueError, json.JSONDecodeError) as exc:
        _stash_output(prompt_file, stdout, stderr)
        raise ValueError(f"{exc}\n(saved grok stdout next to {prompt_file})") from exc


def _stash_output(prompt_file: Path, stdout: str, stderr: str) -> None:
    dest = Path(prompt_file)
    try:
        dest.with_suffix(".stdout.txt").write_text(stdout, encoding="utf-8")
        dest.with_suffix(".stderr.txt").write_text(stderr, encoding="utf-8")
    except OSError:
        return
