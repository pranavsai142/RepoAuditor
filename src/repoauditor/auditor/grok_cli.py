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
DISALLOWED_TOOLS_SOLO = "search_replace,write,Agent"
EXEC_DISALLOWED_TOOLS = "search_replace,write,Agent"
# Keep the tool-schema dump small. This is most of a cold prefill besides cwd skills.
INVESTIGATE_TOOLS = "read_file,grep,list_dir,run_terminal_cmd"
INVESTIGATE_TOOLS_KIDS = "read_file,grep,list_dir,run_terminal_cmd,Agent"
SCORE_TOOLS = "read_file"


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
    json_schema: bool = False,
    model: str | None = None,
    subagents: bool = False,
) -> list[str]:
    # grok opens --prompt-file relative to --cwd (the scanned repo), not process cwd
    prompt = Path(prompt_file).expanduser().resolve()
    # Fresh session id so a TUI `--resume` of an older live run cannot attach
    # to this process (sessions are grouped by --cwd).
    session_id = str(uuid.uuid4())
    turns = max_turns if max_turns is not None else (EXPLORE_MAX_TURNS if explore else EXEC_MAX_TURNS)
    cmd = [
        grok_bin,
        *(["--model", model] if model else []),
        "--prompt-file",
        str(prompt),
        "--session-id",
        session_id,
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
        "--no-memory",
    ]
    if explore:
        cmd.extend(["--tools", INVESTIGATE_TOOLS_KIDS if subagents else INVESTIGATE_TOOLS])
    else:
        cmd.extend(["--tools", SCORE_TOOLS])
    if json_schema:
        payload = schema if schema is not None else AUDITOR_JSON_SCHEMA
        cmd.extend(["--json-schema", json.dumps(payload, separators=(",", ":"))])
    if explore:
        if subagents:
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
                    DISALLOWED_TOOLS_SOLO,
                    "--max-turns",
                    str(turns),
                    "--no-subagents",
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
    """Accept a grok wrapper, raw auditor JSON, fenced JSON, or plain prose."""
    if not raw or not raw.strip():
        raise ValueError("headless grok produced empty stdout")
    fenced = _report_from_fences(raw)
    if fenced:
        return fenced
    candidates = _iter_json_dicts(raw)
    picked = _pick_report_dict(candidates)
    if picked is None:
        if _looks_like_prose(raw):
            return report_from_prose(raw)
        raise ValueError("headless grok JSON had no object")
    if picked.get("type") == "error":
        raise GrokFailed(["grok"], 1, picked.get("message") or raw, raw)
    reason = str(picked.get("stopReason") or picked.get("stop_reason") or "")
    inner = picked.get("structured_output") or picked.get("text")
    if "max_turn" in reason.lower() or reason.lower() == "max_turns":
        recovered = _coerce_payload(inner)
        if recovered:
            return recovered
        if isinstance(inner, str) and _looks_like_prose(inner):
            return report_from_prose(inner)
        raise GrokFailed(["grok"], 1, "max turns reached", raw)
    recovered = _coerce_payload(picked.get("structured_output"))
    if recovered:
        return recovered
    recovered = _coerce_payload(picked.get("text"))
    if recovered:
        return recovered
    if _looks_like_report(picked):
        return picked
    if _looks_like_prose(raw):
        return report_from_prose(_plain_text(picked) or raw)
    raise ValueError("headless grok JSON had no structured_output or text")


def _coerce_payload(value: object) -> dict | None:
    if isinstance(value, dict):
        if _looks_like_report(value):
            return value
        nested = _pick_report_dict(_iter_json_dicts(json.dumps(value)))
        if nested and _looks_like_report(nested):
            return nested
        return None
    if not isinstance(value, str) or not value.strip():
        return None
    fenced = _report_from_fences(value)
    if fenced:
        return fenced
    nested = _pick_report_dict(_iter_json_dicts(value))
    if nested and _looks_like_report(nested):
        return nested
    if _looks_like_prose(value):
        return report_from_prose(value)
    return None


def _plain_text(picked: dict) -> str:
    text = picked.get("text")
    if isinstance(text, str):
        return text
    thought = picked.get("thought")
    if isinstance(thought, str):
        return thought
    return ""


def _looks_like_prose(text: str) -> bool:
    body = text.strip()
    if len(body) < 80:
        return False
    return "\n" in body or len(body) >= 120


def report_from_prose(text: str) -> dict:
    """Local models often cannot emit the auditor schema. Keep the write-up."""
    body = text.strip()
    if body.startswith("```"):
        body = body.strip("`")
        if body.lower().startswith("markdown"):
            body = body[8:].strip()
        elif body.lower().startswith("text"):
            body = body[4:].strip()
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    headline = lines[0][:240] if lines else ""
    return {
        "purpose": "",
        "category": "unknown",
        "headline": headline,
        "executive_summary": body,
        "checklist": [],
        "next_inspect": [],
    }


def _report_from_fences(text: str) -> dict | None:
    opener = "```"
    start = 0
    while True:
        begin = text.find(opener, start)
        if begin < 0:
            return None
        after = text.find("\n", begin)
        if after < 0:
            return None
        end = text.find(opener, after)
        if end < 0:
            return None
        block = text[after + 1 : end].strip()
        nested = _pick_report_dict(_iter_json_dicts(block))
        if nested and _looks_like_report(nested):
            return nested
        start = end + 3


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
    json_schema: bool = False,
    model: str | None = None,
    subagents: bool = False,
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
        json_schema=json_schema,
        model=model,
        subagents=subagents,
    )
    run = runner or subprocess.run
    limit = timeout or 90
    env = os.environ.copy()
    env.setdefault("GROK_CLAUDE_SKILLS_ENABLED", "false")
    env.setdefault("GROK_CURSOR_SKILLS_ENABLED", "false")
    if not subagents:
        env["GROK_SUBAGENTS"] = "0"
    try:
        result = run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=limit,
            env=env,
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
        try:
            return parse_headless_json(stdout)
        except (ValueError, json.JSONDecodeError, GrokFailed):
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
