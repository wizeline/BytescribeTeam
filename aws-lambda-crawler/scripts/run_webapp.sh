#!/usr/bin/env zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -d "webapp/.venv" ]; then
  python -m venv webapp/.venv
fi

source webapp/.venv/bin/activate
pip install -r webapp/requirements.txt

# Prefer poetry if available
if command -v poetry >/dev/null 2>&1; then
  echo "Using poetry to run the webapp"
  (cd webapp && poetry install --no-root || true)
  (cd webapp && poetry run python app.py)
else
  python -m webapp.app
fi
