"""Classify a repo tree as ops / product / docs / scaffold. Agnostic of any vendor."""

from __future__ import annotations

from repoauditor.auditor.substance import path_kind
from repoauditor.patterns.thresholds import is_husk_path

OPS_FRAGMENTS = (
    "logging",
    "logstash",
    "splunk",
    "datadog",
    "sentry",
    "security",
    "/iam/",
    "runbook",
    "playbook",
    "oncall",
    "/slo",
    "terraform",
    "helm/",
    "ansible",
    ".github/workflows",
    "monitoring",
)

REQUIREMENTS_NAMES = {
    "requirements.md",
    "requirement.md",
    "spec.md",
    "rfc.md",
    "week1.md",
    "onboarding.md",
    "sow.md",
}


def is_ops_path(path: str) -> bool:
    lowered = path.lower()
    return any(frag in lowered for frag in OPS_FRAGMENTS)


def is_requirements_path(path: str) -> bool:
    return path.split("/")[-1].lower() in REQUIREMENTS_NAMES


def classify_tree(head_paths: list[str]) -> dict:
    ops = [p for p in head_paths if is_ops_path(p)]
    reqs = [p for p in head_paths if is_requirements_path(p)]
    kinds = [path_kind(p) for p in head_paths]
    docs_only = bool(head_paths) and all(
        k == "docs" or is_husk_path(p) for p, k in zip(head_paths, kinds)
    )
    return {
        "ops_path_count": len(ops),
        "is_ops": len(ops) >= 2,
        "docs_only": docs_only,
        "requirements_paths": reqs,
        "has_requirements": bool(reqs),
    }
