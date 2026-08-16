from __future__ import annotations

from pathlib import Path

from repoauditor.extract import commits_as_dicts, extract_repo
from repoauditor.identity import apply_bots_and_keys, build_identities
from tests.fixtures import spec


def test_aliases_are_two_identities_with_suggestion(department: Path) -> None:
    commits, _ = extract_repo("identity-aliases", department / spec.ALIAS)
    rows = commits_as_dicts(commits)
    apply_bots_and_keys(rows)
    identities, suggestions = build_identities(rows)
    humans = [i for i in identities if not i["is_bot"]]
    assert len(humans) == 2
    emails = {i["author_email"].lower() for i in humans}
    assert emails == spec.ALIAS_EMAILS
    kinds = {s["kind"] for s in suggestions}
    assert "same_name_different_email" in kinds
    assert "noreply_local_part" in kinds
    # suggestions must not collapse the table
    assert len(identities) == 2
