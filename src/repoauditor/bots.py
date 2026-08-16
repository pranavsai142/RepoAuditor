from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

_BOT_WORD = re.compile(r"(?i)\bbot\b")


@lru_cache(maxsize=1)
def default_lists() -> dict:
    path = Path(__file__).with_name("bots_default.json")
    return json.loads(path.read_text(encoding="utf-8"))


def classify_bot(name: str, email: str) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    lowered_name = name.lower()
    lowered_email = email.lower()
    local, _, domain = lowered_email.partition("@")
    if "[bot]" in lowered_name or "[bot]" in lowered_email:
        reasons.append("name_or_email_contains_[bot]")
    if _BOT_WORD.search(name) or _BOT_WORD.search(email):
        reasons.append("word_bot")
    lists = default_lists()
    if local in lists["local_parts"]:
        reasons.append(f"local_part:{local}")
    if domain in lists["domains"]:
        reasons.append(f"domain:{domain}")
    # dependabot+id@users.noreply.github.com
    local_root = local.split("+", 1)[0]
    if local_root in lists["local_parts"]:
        reasons.append(f"local_part:{local_root}")
    return (len(reasons) > 0, reasons)
