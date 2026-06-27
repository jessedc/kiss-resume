#!/usr/bin/env bash
# Apply safe auto-fixes: ruff format + ruff check --fix.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "→ ruff format";       uv run ruff format .
echo "→ ruff check --fix";  uv run ruff check --fix .
echo; echo "Done. Run ./scripts/check.sh to verify the full gate is green."
