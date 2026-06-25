#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PY:-python3}"
if [ ! -d .venv ]; then
  "$PY" -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
.venv/bin/pytest tests/ -q
echo "[ci] PAC agent eval catalog"
.venv/bin/python scripts/run_pac_agent_eval.py --check-catalog
echo "[ci] PAC agent evals (Onda 5.4)"
.venv/bin/pytest tests/unit/test_pac_agent_eval_cases.py tests/unit/test_run_pac_agent_eval_script.py -q
echo "[ci] OpenAPI Onda 1 registry"
.venv/bin/python -m pytest tests/unit/test_openapi_onda1_paths.py -q
echo "[ci] OpenAPI analista GPT (≤30 operações)"
.venv/bin/python scripts/audit_pac_openapi_operation_limit.py --check
.venv/bin/python -m pytest tests/unit/test_pac_openapi_operation_limit.py tests/unit/test_pac_api_key_auth.py -q
