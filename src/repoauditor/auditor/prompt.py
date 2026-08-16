"""Financial-auditor persona + background-check prompt for headless Grok."""

from __future__ import annotations

import json
from pathlib import Path

from repoauditor import CAVEAT

PROTOCOL = """
OPERATING PROTOCOL — same steps on every repo. The pack is the entire world.

P0. Do not call tools. Do not search. Do not recount commits, lines, or people.
P1. Treat metrics, findings, substance, and file excerpts as given facts.
P2. Compare README claims to head_paths, source_samples, and workflow_files.
P3. Answer every checklist id in order. One or two sentences. If the pack cannot support it: "cannot tell from pack".
P4. See through the veil: volume is not work; comments are not a product; a scaffold is not a replacement suite; assistant trailers are not a team.
P5. No preamble, no investigation narrative, no hedging essay. JSON only.

You add comprehension of THIS tree. You do not invent a second investigation.
"""

SYSTEM_PROMPT = """You interpret one repository pack. Scripts already collected the metrics.

""" + PROTOCOL + """

""" + CAVEAT + """
"""

EXECUTIVE_SYSTEM_PROMPT = """You write one department executive summary from the metric pack.

Same protocol: no tools, no recount, no search. Comprehend the numbers and the per-repo flags. Separate run-the-business shared services from demo/requirements theater. Name who carries durable repos vs who hops thin greenfields.

No preamble. JSON only.

""" + CAVEAT + """
"""


def load_checklist() -> list[dict]:
    path = Path(__file__).with_name("checklist.json")
    return json.loads(path.read_text(encoding="utf-8"))


def user_prompt(pack: dict) -> str:
    items = "\n".join(f"- `{item['id']}`: {item['question']}" for item in load_checklist())
    return (
        "Follow the operating protocol. Answer the checklist from this pack only.\n\n"
        f"## Checklist\n{items}\n\n"
        "## Evidence pack (JSON)\n"
        f"{json.dumps(pack, indent=2, sort_keys=True)}\n"
    )


def executive_prompt(pack: dict) -> str:
    return (
        "Follow the protocol. One executive summary from this pack. No tools.\n\n"
        f"{json.dumps(pack, indent=2, sort_keys=True)}\n"
    )
