"""v1 detector constants. Change here, not as hidden magic in if-statements."""

from __future__ import annotations

import re
from fnmatch import fnmatch

WIP_RE = re.compile(r"(?i)\bwip\b")

HUSK_MAX_COMMITS = 3
HUSK_ALLOWED = (
    "README*",
    "LICENSE*",
    "COPYING*",
    ".gitignore",
    ".gitattributes",
    ".editorconfig",
)

WIP_MIN_COMMITS = 8
WIP_SUBJECT_SHARE = 0.50

BOT_MIN_COMMITS = 3
BOT_HUMAN_SHARE_MAX = 0.15

PADDING_MIN_COMMITS = 5
PADDING_MIN_SOLO_DAYS = 5
PADDING_CLUSTER_MIN = 3
PADDING_CLUSTER_SHARE = 0.50

HOT_STREAK_MIN = 3
HOT_STREAK_MAX = 21
HOT_GAP_MIN = 7

FADE_MIN_DAYS = 10
FADE_MIN_SPAN = 21
FADE_DENSITY = 0.40
FADE_SILENCE = 30

ISLAND_MIN_HUMAN_COMMITS = 5

BURST_WINDOW_DAYS = 14
BURST_MIN_COMMITS = 8
BURST_SILENCE = 45

SUBSTANCE_MIN_COMMITS = 3
SUBSTANCE_NO_CODE_SHARE = 0.70

AI_MIN_COMMITS = 4
AI_SHARE = 0.50

SCAFFOLD_MARKERS = (
    "vite.svg",
    "vite.config.ts",
    "vite.config.js",
    "src/App.tsx",
    "src/App.jsx",
    "src/logo.svg",
)
REPLACE_RE = re.compile(
    r"(?i)\b(replac\w*|next-gen|next gen|rewrite|moderni[sz]e|legacy|platform)\b"
)

HOP_MIN_REPOS = 3
HOP_MAX_SPAN_DAYS = 21


def is_husk_path(path: str) -> bool:
    name = path.split("/")[-1]
    for pattern in HUSK_ALLOWED:
        if fnmatch(name.lower(), pattern.lower()):
            return True
    return False
