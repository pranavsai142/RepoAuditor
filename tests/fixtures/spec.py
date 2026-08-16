from __future__ import annotations

AS_OF = "2024-07-01"
REPO_COUNT = 17

REPOS = [
    "ai-demo",
    "bot-operated",
    "burst-graveyard",
    "comment-docs",
    "commit-padding",
    "contributor-fade",
    "greenfield-a",
    "greenfield-b",
    "healthy-team",
    "hot-potato",
    "identity-aliases",
    "nested/deep/nested-husk",
    "one-person-island",
    "perpetual-wip",
    "readme-husk",
    "requirements-week",
    "shared-ops",
]

# Required flags (other flags may also fire on the same fixture).
REQUIRED_FLAGS = {
    "readme-husk": {"readme_husk"},
    "nested/deep/nested-husk": {"readme_husk"},
    "perpetual-wip": {"perpetual_wip"},
    "bot-operated": {"bot_operated"},
    "commit-padding": {"commit_padding"},
    "hot-potato": {"hot_potato"},
    "one-person-island": {"one_person_island"},
    "burst-graveyard": {"burst_graveyard"},
    "comment-docs": {"low_substance"},
    "ai-demo": {"ai_dominated", "demo_replacement"},
    "requirements-week": {"requirements_theater"},
}

REQUIRED_PERSON_FLAGS = {
    "contributor_fade": "Frank Fade",
    "greenfield_hop": "Quinn Hop",
}

HEALTHY = "healthy-team"
ALIAS = "identity-aliases"
ALIAS_NAME = "Sam Smith"
ALIAS_EMAILS = {"sam@corp.com", "sam@users.noreply.github.com"}
