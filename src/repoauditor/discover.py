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
    # Pointed at a repo → that repo only. Nested .git (submodules, vendored
    # clones) are not extra department members.
    if is_git_repo(root):
        return [{"repo_id": root.name, "path": str(root)}]
    found: list[Path] = []
    _walk(root, root, 0, found)
    repos = []
    for path in found:
        repo_id = path.relative_to(root).as_posix()
        repos.append({"repo_id": repo_id, "path": str(path)})
    return repos
