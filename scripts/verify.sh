#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v git >/dev/null 2>&1; then
  echo "git is required on PATH" >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required on PATH (https://docs.astral.sh/uv/getting-started/installation/)" >&2
  exit 1
fi

uv sync --frozen --group dev
uv run python tests/fixtures/build_fixtures.py
uv run pytest tests/ -q
