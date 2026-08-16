"""Thin subprocess wrapper. The argv is the oracle; nothing here invents git semantics."""

from __future__ import annotations

import subprocess
from pathlib import Path


class GitError(RuntimeError):
    def __init__(self, cmd: list[str], returncode: int, stderr: str):
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"git failed ({returncode}): {' '.join(cmd)}\n{stderr}")


def git_version() -> str:
    result = subprocess.run(
        ["git", "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GitError(["git", "--version"], result.returncode, result.stderr)
    return result.stdout.strip()


def run_git(
    repo: Path | None,
    *args: str,
    input_text: str | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    cmd: list[str] = ["git"]
    if repo is not None:
        cmd.extend(["-C", str(repo)])
    cmd.extend(args)
    result = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        input=input_text,
    )
    if check and result.returncode != 0:
        raise GitError(cmd, result.returncode, result.stderr)
    return result
