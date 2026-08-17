"""Thin subprocess wrapper. The argv is the oracle; nothing here invents git semantics."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

# Inherited GIT_* vars override `git -C <repo>` and would make extract read the wrong tree.
_UNSET_GIT_ENV = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
)


class GitError(RuntimeError):
    def __init__(self, cmd: list[str], returncode: int, stderr: str):
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"git failed ({returncode}): {' '.join(cmd)}\n{stderr}")


def _git_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in _UNSET_GIT_ENV:
        env.pop(key, None)
    return env


def _cmd(repo: Path | None, args: tuple[str, ...]) -> list[str]:
    cmd: list[str] = ["git"]
    if repo is not None:
        cmd.extend(["-C", str(repo)])
    cmd.extend(args)
    return cmd


def git_version() -> str:
    result = subprocess.run(
        ["git", "--version"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_git_env(),
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
    cmd = _cmd(repo, args)
    result = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        input=input_text,
        env=_git_env(),
    )
    if check and result.returncode != 0:
        raise GitError(cmd, result.returncode, result.stderr)
    return result


def run_git_bytes(
    repo: Path | None,
    *args: str,
    input_bytes: bytes | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    """Raw stdout/stdin. Use for `git show --patch` / `git patch-id` (file bytes, not UTF-8)."""
    cmd = _cmd(repo, args)
    result = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        input=input_bytes,
        env=_git_env(),
    )
    if check and result.returncode != 0:
        err = (result.stderr or b"").decode("utf-8", errors="replace")
        raise GitError(cmd, result.returncode, err)
    return result
