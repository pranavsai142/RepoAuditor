"""Invoke Grok Build in headless mode (`grok --prompt-file`)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable

from repoauditor.auditor.schema import AUDITOR_JSON_SCHEMA

# One model response. No tool loop. The pack already contains files.
DEFAULT_MAX_TURNS = "1"
DISALLOWED_TOOLS = (
    "read_file,grep,list_dir,run_terminal_cmd,web_search,web_fetch,"
    "search_replace,write,Agent"
)


class GrokNotFound(RuntimeError):
    pass


class GrokFailed(RuntimeError):
    def __init__(self, cmd: list[str], returncode: int, stderr: str, stdout: str):
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr
        self.stdout = stdout
        super().__init__(f"headless grok failed ({returncode}): {' '.join(cmd)}\n{stderr}")


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
) -> list[str]:
    schema = schema or AUDITOR_JSON_SCHEMA
    return [
        grok_bin,
        "--prompt-file",
        str(prompt_file),
        "--json-schema",
        json.dumps(schema, separators=(",", ":")),
        "--output-format",
        "json",
        "--system-prompt-override",
        system_prompt,
        "--cwd",
        str(cwd),
        "--disallowed-tools",
        DISALLOWED_TOOLS,
        "--max-turns",
        DEFAULT_MAX_TURNS,
        "--no-plan",
        "--no-subagents",
        "--disable-web-search",
        "--no-auto-update",
        "--verbatim",
        "--yolo",
    ]


def parse_headless_json(raw: str) -> dict:
    data = json.loads(raw)
    if isinstance(data, dict) and data.get("type") == "error":
        raise GrokFailed(["grok"], 1, data.get("message") or raw, raw)
    if isinstance(data, dict) and "structured_output" in data and data["structured_output"]:
        out = data["structured_output"]
        return out if isinstance(out, dict) else json.loads(out)
    text = data.get("text") if isinstance(data, dict) else None
    if isinstance(text, dict):
        return text
    if isinstance(text, str) and text.strip():
        return _parse_json_object(text)
    raise ValueError("headless grok JSON had no structured_output or text")


def _parse_json_object(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        value = json.loads(text[start : end + 1])
        if isinstance(value, dict):
            return value
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
) -> dict:
    binary = find_grok(grok_bin)
    cmd = build_cmd(
        grok_bin=binary,
        prompt_file=prompt_file,
        system_prompt=system_prompt,
        cwd=cwd,
        schema=schema,
    )
    run = runner or subprocess.run
    result = run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout or 90,
    )
    if result.returncode != 0:
        raise GrokFailed(cmd, result.returncode, result.stderr or "", result.stdout or "")
    return parse_headless_json(result.stdout)
