#!/usr/bin/env python3
"""Build the fixture department: real git repos with pinned author dates."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "department"

ALICE = ("Alice Auditor", "alice@dept.test")
BOB = ("Bob Wipper", "bob@dept.test")
CAROL = ("Carol Padder", "carol@dept.test")
DAVE = ("Dave First", "dave@dept.test")
EVE = ("Eve Second", "eve@dept.test")
FRANK = ("Frank Fade", "frank@dept.test")
GRACE = ("Grace Solo", "grace@dept.test")
HANK = ("Hank Burst", "hank@dept.test")
IVY = ("Ivy Team", "ivy@dept.test")
JACK = ("Jack Team", "jack@dept.test")
KIM = ("Kim Team", "kim@dept.test")
NED = ("Ned Notes", "ned@dept.test")
PAT = ("Pat Prompt", "pat@dept.test")
QUINN = ("Quinn Hop", "quinn@dept.test")
OPS1 = ("Omar Ops", "omar@dept.test")
OPS2 = ("Rita Reliability", "rita@dept.test")
SAM = "Sam Smith"
BOT = ("dependabot[bot]", "49699333+dependabot[bot]@users.noreply.github.com")


def run(repo: Path, *args: str, env: dict | None = None) -> None:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    subprocess.run(["git", *args], cwd=repo, check=True, env=merged, capture_output=True)


def init_repo(path: Path) -> Path:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    subprocess.run(
        ["git", "-c", "init.defaultBranch=main", "init"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    run(path, "config", "user.name", "fixture")
    run(path, "config", "user.email", "fixture@dept.test")
    run(path, "config", "commit.gpgsign", "false")
    return path


def iso(day: date, hour: int = 12) -> str:
    return f"{day.isoformat()}T{hour:02d}:00:00+00:00"


def commit(
    repo: Path,
    person: tuple[str, str],
    day: date,
    message: str,
    files: dict[str, str] | None = None,
    allow_empty: bool = False,
    hour: int = 12,
) -> None:
    name, email = person
    stamp = iso(day, hour)
    env = {
        "GIT_AUTHOR_NAME": name,
        "GIT_AUTHOR_EMAIL": email,
        "GIT_AUTHOR_DATE": stamp,
        "GIT_COMMITTER_NAME": name,
        "GIT_COMMITTER_EMAIL": email,
        "GIT_COMMITTER_DATE": stamp,
    }
    if files:
        for rel, content in files.items():
            dest = repo / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            run(repo, "add", rel)
    args = ["commit", "-m", message]
    if allow_empty:
        args.append("--allow-empty")
    run(repo, *args, env=env)


def weekdays(start: date, end: date) -> list[date]:
    days = []
    cur = start
    while cur <= end:
        if cur.weekday() < 5:
            days.append(cur)
        cur += timedelta(days=1)
    return days


def build_readme_husk(path: Path, person=ALICE) -> None:
    init_repo(path)
    commit(path, person, date(2024, 1, 2), "init", {"README.md": "# Maybe later\n"})
    commit(path, person, date(2024, 1, 3), "tweak readme", {"README.md": "# Still a stub\n"})


def build_perpetual_wip(path: Path) -> None:
    init_repo(path)
    for i in range(12):
        day = date(2024, 1, 8) + timedelta(days=i * 3)
        msg = f"WIP feature slice {i}" if i < 8 else f"keep going {i}"
        commit(path, BOB, day, msg, {"app.py": f"# step {i}\nprint({i})\n"})


def build_bot_operated(path: Path) -> None:
    init_repo(path)
    commit(path, ALICE, date(2024, 2, 1), "seed", {"pkg/__init__.py": "x = 1\n"})
    for i in range(10):
        day = date(2024, 2, 2) + timedelta(days=i)
        commit(
            path,
            BOT,
            day,
            f"chore(deps): bump thing {i}",
            {"pkg/lock.txt": f"dep=={i}\n"},
        )


def build_commit_padding(path: Path) -> None:
    init_repo(path)
    commit(path, CAROL, date(2024, 3, 3), "seed", {"keep.txt": "same\n"})
    for i in range(8):
        day = date(2024, 3, 4) + timedelta(days=i)
        commit(path, CAROL, day, f"daily status {i}", allow_empty=True)


def build_hot_potato(path: Path) -> None:
    init_repo(path)
    for i in range(12):
        day = date(2024, 2, 1) + timedelta(days=i)
        commit(path, DAVE, day, f"dave day {i}", {"work.py": f"# dave {i}\n"})
    for i in range(14):
        day = date(2024, 3, 1) + timedelta(days=i)
        commit(path, EVE, day, f"eve day {i}", {"work.py": f"# eve {i}\n"})


def build_contributor_fade(path: Path) -> None:
    init_repo(path)
    for i, day in enumerate(weekdays(date(2024, 3, 1), date(2024, 5, 31))):
        commit(path, FRANK, day, f"daily {day.isoformat()}", {"tracker.py": f"# {i}\n"})


def build_one_person_island(path: Path) -> None:
    init_repo(path)
    for i in range(15):
        day = date(2024, 4, 1) + timedelta(days=i)
        commit(path, GRACE, day, f"real work {i}", {"lib.py": f"def f{i}():\n    return {i}\n"})
    commit(path, BOT, date(2024, 4, 20), "chore(deps)", {"lib.py": "def f14():\n    return 14\n# bot\n"})
    commit(path, BOT, date(2024, 6, 20), "chore(deps)", {"deps.txt": "x==1\n"})


def build_burst_graveyard(path: Path) -> None:
    init_repo(path)
    for i in range(12):
        day = date(2024, 1, 8) + timedelta(days=i)
        commit(path, HANK, day, f"burst {i}", {"src.c": f"int x = {i};\n"})


def build_healthy(path: Path) -> None:
    init_repo(path)
    people = [IVY, JACK, KIM]
    for week in range(6):
        for idx, person in enumerate(people):
            day = date(2024, 5, 20) + timedelta(days=week * 6 + idx)
            commit(
                path,
                person,
                day,
                f"{person[0].split()[0].lower()} increment {week}",
                {f"{person[0].split()[0].lower()}.py": f"# week {week} by {person[0]}\nvalue = {week}\n"},
            )
    commit(
        path,
        IVY,
        date(2024, 6, 28),
        "ship increment",
        {"ivy.py": "# shipped\nvalue = 99\n"},
    )


def build_ai_demo(path: Path) -> None:
    init_repo(path)
    trailer = "\n\nCo-authored-by: Cursor <cursoragent@cursor.com>\n"
    commit(
        path,
        PAT,
        date(2024, 6, 2),
        "init next-gen replacement platform" + trailer,
        {
            "README.md": (
                "# Next-gen replacement platform\n\n"
                "Modernize and replace the legacy enterprise system.\n"
            ),
            "index.html": "<html><body><div id='app'></div></body></html>\n",
            "vite.config.ts": "export default {}\n",
            "src/App.tsx": "export default function App() { return <h1>Vite + React</h1> }\n",
            "vite.svg": "<svg></svg>\n",
        },
    )
    for i in range(5):
        commit(
            path,
            PAT,
            date(2024, 6, 3 + i),
            f"cursor: tweak demo {i}" + trailer,
            {"src/App.tsx": f"export default function App() {{ return <h1>Demo {i}</h1> }}\n"},
        )


def build_comment_docs(path: Path) -> None:
    init_repo(path)
    commit(
        path,
        NED,
        date(2024, 6, 1),
        "init trading engine",
        {
            "README.md": "# Apex Trading Engine\n\nProduction matching engine for live markets.\n",
            "engine.py": "# matching engine entry\n# TODO implement\n# still planning\n",
        },
    )
    body = "# matching engine entry\n# TODO implement\n# still planning\n"
    for i in range(5):
        body += f"# status ping {i}\n"
        commit(
            path,
            NED,
            date(2024, 6, 2 + i),
            f"refine engine comments {i}",
            {"engine.py": body},
        )
    commit(
        path,
        NED,
        date(2024, 6, 10),
        "add notes",
        {"NOTES.md": "Standup: still designing the matching engine.\n"},
    )


def build_requirements_week(path: Path) -> None:
    init_repo(path)
    text = "# Week 1 requirements\n\nReplace the commercial suite with a custom platform.\n"
    for i in range(5):
        text += f"\n## Day {i} notes\nStill gathering requirements. No implementation.\n"
        commit(
            path,
            QUINN,
            date(2024, 4, 1) + timedelta(days=i),
            f"week 1 requirements day {i}",
            {"REQUIREMENTS.md": text},
        )


def build_greenfield(path: Path, start: date, label: str) -> None:
    init_repo(path)
    for i in range(6):
        commit(
            path,
            QUINN,
            start + timedelta(days=i),
            f"{label} spike {i}",
            {"main.py": f"print({i!r})\n"},
        )


def build_shared_ops(path: Path) -> None:
    init_repo(path)
    commit(
        path,
        OPS1,
        date(2024, 1, 8),
        "logging collector",
        {"logging/collector.py": "def emit(event):\n    return event\n"},
    )
    commit(
        path,
        OPS2,
        date(2024, 2, 5),
        "security baseline",
        {"security/iam.md": "# IAM roles for shared services\n"},
    )
    commit(
        path,
        OPS1,
        date(2024, 3, 4),
        "oncall runbook",
        {"runbook.md": "# Page on 5xx\n"},
    )
    commit(
        path,
        OPS2,
        date(2024, 6, 20),
        "ci for shared services",
        {".github/workflows/ci.yml": "name: ci\non: [push]\njobs: {}\n"},
    )


def build_aliases(path: Path) -> None:
    init_repo(path)
    corp = (SAM, "sam@corp.com")
    noreply = (SAM, "sam@users.noreply.github.com")
    for i in range(3):
        commit(path, corp, date(2024, 5, 1) + timedelta(days=i), f"corp {i}", {"a.py": f"# c{i}\n"})
    for i in range(3):
        commit(path, noreply, date(2024, 5, 10) + timedelta(days=i), f"noreply {i}", {"a.py": f"# n{i}\n"})


def build(dest: Path | None = None) -> Path:
    dest = dest or ROOT
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    build_readme_husk(dest / "readme-husk")
    build_perpetual_wip(dest / "perpetual-wip")
    build_bot_operated(dest / "bot-operated")
    build_commit_padding(dest / "commit-padding")
    build_hot_potato(dest / "hot-potato")
    build_contributor_fade(dest / "contributor-fade")
    build_one_person_island(dest / "one-person-island")
    build_burst_graveyard(dest / "burst-graveyard")
    build_healthy(dest / "healthy-team")
    build_aliases(dest / "identity-aliases")
    build_comment_docs(dest / "comment-docs")
    build_ai_demo(dest / "ai-demo")
    build_requirements_week(dest / "requirements-week")
    build_greenfield(dest / "greenfield-a", date(2024, 2, 1), "alpha")
    build_greenfield(dest / "greenfield-b", date(2024, 3, 1), "beta")
    build_shared_ops(dest / "shared-ops")
    build_readme_husk(dest / "nested" / "deep" / "nested-husk", person=ALICE)
    return dest


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT
    built = build(target)
    print(f"built {built}")
