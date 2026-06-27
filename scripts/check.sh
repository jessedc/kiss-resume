#!/usr/bin/env bash
# Validate: format check + lint + tests + static type analysis.
#   ./scripts/check.sh         # check everything (read-only)
#   ./scripts/check.sh --fix   # apply safe auto-fixes first, then check
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ "${1:-}" == "--fix" ]]; then
  echo "→ ruff format (applying)";        uv run ruff format .
  echo "→ ruff check --fix (applying)";    uv run ruff check --fix .
fi

echo "→ ruff format --check"; uv run ruff format --check .
echo "→ ruff check";          uv run ruff check .
echo "→ pytest";              uv run pytest
echo "→ mypy";                uv run mypy
echo "→ pyright";             uv run pyright
echo; echo "✓ all checks passed (format + lint + tests + types)"
