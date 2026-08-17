"""JSON Schema for headless grok --json-schema (structured auditor report)."""

from __future__ import annotations

CHECKLIST_IDS = (
    "purpose",
    "category",
    "head_substance",
    "commit_substance",
    "readme_match",
    "wip_theater",
    "bot_vs_human",
    "padding",
    "occupancy",
    "ai_assistance",
    "demo_vs_durable",
    "run_the_business",
    "requirements_theater",
    "greenfield_vs_buy",
    "next_inspect",
)

CATEGORIES = (
    "service",
    "library",
    "script",
    "infra",
    "docs",
    "experiment",
    "husk",
    "unknown",
)

def _item_list(name_key: str) -> dict:
    return {
        "type": "array",
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": [name_key, "why"],
            "properties": {
                name_key: {"type": "string"},
                "why": {"type": "string"},
            },
        },
    }


EXECUTIVE_JSON_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "headline",
        "executive_summary",
        "run_the_business",
        "theater",
        "who_matters",
        "who_to_inspect",
        "assistance",
        "unscriptable",
        "open_next",
    ],
    "properties": {
        "headline": {"type": "string"},
        "executive_summary": {"type": "string"},
        "run_the_business": _item_list("repo_id"),
        "theater": _item_list("repo_id"),
        "who_matters": _item_list("name"),
        "who_to_inspect": _item_list("name"),
        "assistance": {"type": "string"},
        "unscriptable": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["observation", "evidence"],
                "properties": {
                    "observation": {"type": "string"},
                    "evidence": {"type": "string"},
                },
            },
        },
        "open_next": {"type": "array", "items": {"type": "string"}},
    },
}


AUDITOR_JSON_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["purpose", "category", "headline", "executive_summary", "checklist", "next_inspect"],
    "properties": {
        "purpose": {"type": "string"},
        "category": {"type": "string", "enum": list(CATEGORIES)},
        "headline": {"type": "string"},
        "executive_summary": {"type": "string"},
        "checklist": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "answer", "concern", "evidence_hashes", "evidence_paths"],
                "properties": {
                    "id": {"type": "string", "enum": list(CHECKLIST_IDS)},
                    "answer": {"type": "string"},
                    "concern": {"type": "boolean"},
                    "evidence_hashes": {"type": "array", "items": {"type": "string"}},
                    "evidence_paths": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "next_inspect": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["hash", "why"],
                "properties": {
                    "hash": {"type": "string"},
                    "why": {"type": "string"},
                },
            },
        },
    },
}
