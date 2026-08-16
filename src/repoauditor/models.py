from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def to_dict(obj: Any) -> dict[str, Any]:
    return asdict(obj)


@dataclass
class FileChange:
    path: str
    additions: int | None
    deletions: int | None
    is_binary: bool


@dataclass
class Commit:
    repo_id: str
    hash: str
    tree: str
    parents: list[str]
    is_merge: bool
    author_name: str
    author_email: str
    author_date: str
    committer_name: str
    committer_email: str
    committer_date: str
    subject: str
    trailers: str = ""
    files: list[FileChange] = field(default_factory=list)
    additions: int | None = None
    deletions: int | None = None
    net: int | None = None
    churn: int | None = None
    files_changed: int = 0
    patch_id: str | None = None
    identity_key: str = ""
    is_bot: bool = False
    bot_reasons: list[str] = field(default_factory=list)


def volume_of(files: list[FileChange]) -> tuple[int | None, int | None, int | None, int | None, int]:
    adds = 0
    dels = 0
    saw_int = False
    for change in files:
        if change.is_binary or change.additions is None or change.deletions is None:
            continue
        adds += change.additions
        dels += change.deletions
        saw_int = True
    if not saw_int:
        return None, None, None, None, len(files)
    return adds, dels, adds - dels, adds + dels, len(files)
