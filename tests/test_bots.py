from __future__ import annotations

from pathlib import Path

from repoauditor.bots import classify_bot
from repoauditor.extract import commits_as_dicts, extract_repo
from repoauditor.identity import apply_bots_and_keys


def test_dependabot_is_bot_carol_is_not() -> None:
    is_bot, reasons = classify_bot(
        "dependabot[bot]",
        "49699333+dependabot[bot]@users.noreply.github.com",
    )
    assert is_bot
    assert reasons
    assert classify_bot("Carol Padder", "carol@dept.test") == (False, [])


def test_bots_remain_in_raw(department: Path) -> None:
    commits, _ = extract_repo("bot-operated", department / "bot-operated")
    rows = commits_as_dicts(commits)
    apply_bots_and_keys(rows)
    assert len(rows) == 11
    bots = [c for c in rows if c["is_bot"]]
    humans = [c for c in rows if not c["is_bot"]]
    assert len(bots) == 10
    assert len(humans) == 1
    assert humans[0]["author_name"] == "Alice Auditor"
