#!/usr/bin/env bash
# One-command start for macOS / Linux
set -e
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
if [ ! -d .venv ]; then
  echo "Creating virtual environment ..."
  $PY -m venv .venv
fi
. .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
[ -f .env ] || cp .env.example .env
python -m gcx setup "$@"
python -m gcx serve --port "${PORT:-8000}"
