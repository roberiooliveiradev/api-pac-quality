#!/usr/bin/env bash
# Smoke: delegação api-pac → api-delpi (requer stack delpi + api-pac com override).
set -euo pipefail

PAC_BASE_URL="${PAC_BASE_URL:-http://localhost:8082}"
PAC_API_KEY="${PAC_QUALITY_API_KEY:-local-pac-dev-key}"

echo "==> Health api-pac"
health="$(curl -sf "${PAC_BASE_URL}/health")"
echo "${health}" | python3 -m json.tool

delegation="$(echo "${health}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('api_delpi_delegation',''))")"
if [[ "${delegation}" != "enabled" ]]; then
  echo "WARN: api_delpi_delegation=${delegation} — configure API_DELPI_* no .env e PAC_DELEGATE_TRANSACTIONAL_TO_API_DELPI=true"
  exit 0
fi

echo "==> Listar planos (delegado)"
curl -sf -H "X-Api-Key: ${PAC_API_KEY}" \
  "${PAC_BASE_URL}/quality/action-plans?page_size=1" | python3 -m json.tool | head -20

echo "==> Buscar usuários atribuíveis"
curl -sf -H "X-Api-Key: ${PAC_API_KEY}" \
  "${PAC_BASE_URL}/quality/action-plans/assignable-users?q=ana&limit=5" | python3 -m json.tool

echo "OK smoke pac-delpi"
