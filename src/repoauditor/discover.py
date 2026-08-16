"""Find git repos inside an operator-supplied directory. No remotes."""

from __future__ import annotations

from pathlib import Path

SKIP_NAMES = frozenset({".git", "node_modules", ".venv", "venv", "__pycache__"})
MAX_DEPTH = 8


def is_git_repo(path: Path) -> bool:
    return (path / ".git").exists()


def _walk(root: Path, current: Path, depth: int, found: list[Path]) -> None:
    if depth > MAX_DEPTH:
        return
    if current != root and is_git_repo(current):
        found.append(current)
        return
    try:
        children = sorted(current.iterdir(), key=lambda p: p.name)
    except OSError:
        return
    for child in children:
        if not child.is_dir() or child.name in SKIP_NAMES:
            continue
        _walk(root, child, depth + 1, found)


def discover(input_dir: Path) -> list[dict[str, str]]:
    root = input_dir.expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"not a directory: {root}")
    found: list[Path] = []
    _walk(root, root, 0, found)
    if not found and is_git_repo(root):
        found = [root]
    repos = []
    for path in found:
        rel = path.relative_to(root)
        repo_id = "." if rel == Path(".") else rel.as_posix()
        repos.append({"repo_id": repo_id, "path": str(path)})
    return repos
