from __future__ import annotations

from repoauditor.assistants import apply_assistants
from repoauditor.bots import classify_bot


def identity_key(name: str, email: str) -> str:
    return f"{name}\t{email.lower()}"


def apply_bots_and_keys(commits: list[dict]) -> None:
    for commit in commits:
        commit["identity_key"] = identity_key(commit["author_name"], commit["author_email"])
        is_bot, reasons = classify_bot(commit["author_name"], commit["author_email"])
        commit["is_bot"] = is_bot
        commit["bot_reasons"] = reasons
    apply_assistants(commits)


def build_identities(commits: list[dict]) -> tuple[list[dict], list[dict]]:
    by_key: dict[str, dict] = {}
    for commit in commits:
        key = commit["identity_key"]
        entry = by_key.setdefault(
            key,
            {
                "identity_key": key,
                "author_name": commit["author_name"],
                "author_email": commit["author_email"],
                "is_bot": commit["is_bot"],
                "bot_reasons": list(commit["bot_reasons"]),
                "commit_count": 0,
            },
        )
        entry["commit_count"] += 1
        if commit["is_bot"]:
            entry["is_bot"] = True
            for reason in commit["bot_reasons"]:
                if reason not in entry["bot_reasons"]:
                    entry["bot_reasons"].append(reason)
    identities = sorted(by_key.values(), key=lambda i: i["identity_key"])
    return identities, _suggestions(identities)


def _suggestions(identities: list[dict]) -> list[dict]:
    by_email: dict[str, list[dict]] = {}
    by_name: dict[str, list[dict]] = {}
    by_local: dict[str, list[dict]] = {}
    for ident in identities:
        email = ident["author_email"].lower()
        by_email.setdefault(email, []).append(ident)
        by_name.setdefault(ident["author_name"].casefold(), []).append(ident)
        local = email.split("@", 1)[0].split("+", 1)[0]
        if local:
            by_local.setdefault(local, []).append(ident)
    suggestions: list[dict] = []
    for email, group in by_email.items():
        if len({i["author_name"] for i in group}) > 1:
            suggestions.append(
                {
                    "kind": "same_email_different_name",
                    "email": email,
                    "identity_keys": [i["identity_key"] for i in group],
                }
            )
    for name, group in by_name.items():
        if len({i["author_email"].lower() for i in group}) > 1:
            suggestions.append(
                {
                    "kind": "same_name_different_email",
                    "name": group[0]["author_name"],
                    "identity_keys": [i["identity_key"] for i in group],
                }
            )
    for local, group in by_local.items():
        emails = {i["author_email"].lower() for i in group}
        if len(emails) > 1 and any("noreply" in i["author_email"].lower() for i in group):
            suggestions.append(
                {
                    "kind": "noreply_local_part",
                    "local_part": local,
                    "identity_keys": [i["identity_key"] for i in group],
                }
            )
    return suggestions
