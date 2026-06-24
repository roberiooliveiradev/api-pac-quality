#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PY:-python3}"
if [ ! -d .venv ]; then
  "$PY" -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
.venv/bin/pytest tests/ -q
