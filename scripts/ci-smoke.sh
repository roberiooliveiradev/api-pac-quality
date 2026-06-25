#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PY:-python3}"
if [ ! -d .venv ]; then
  "$PY" -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
.venv/bin/pytest tests/ -q
echo "[ci] PAC agent evals (Onda 5.4)"
.venv/bin/pytest tests/unit/test_pac_agent_eval_cases.py -q
echo "[ci] OpenAPI Onda 1 registry"
.venv/bin/python -m pytest tests/unit/test_openapi_onda1_paths.py -q
