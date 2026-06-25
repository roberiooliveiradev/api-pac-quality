#!/usr/bin/env bash
# Pós-deploy srv-api — valida OpenAPI Onda 1 e orienta H2 + sync GPT.
set -euo pipefail

PAC_API_URL="${PAC_API_URL:-https://pac-api.minhadelpi.com.br}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DELPI_ROOT="$(cd "${REPO_ROOT}/../delpi-central" && pwd)"

echo "== API PAC pós-deploy (Onda 1 / H2) =="
echo "URL: ${PAC_API_URL}"
echo ""

if [ -f "${DELPI_ROOT}/scripts/homologacao/check-pac-api-server.sh" ]; then
  PAC_API_URL="${PAC_API_URL}" bash "${DELPI_ROOT}/scripts/homologacao/check-pac-api-server.sh"
else
  echo "[warn] check-pac-api-server.sh não encontrado em delpi-central"
fi

echo ""
echo "[check] Imagem local (opcional) — rotas no build atual"
if docker image inspect api-pac-quality:onda1-verify >/dev/null 2>&1; then
  echo "  OK imagem api-pac-quality:onda1-verify presente"
else
  echo "  Dica: cd ../.. && docker build -f api-pac-quality/Dockerfile -t api-pac-quality:onda1-verify ."
fi

echo ""
echo "Próximos passos:"
echo "  1. export PAC_QUALITY_API_KEY=<token do .env srv-api>"
echo "  2. python3 ${DELPI_ROOT}/scripts/homologacao/run_h2_pac_api_smoke.py"
echo "  3. docker exec delpi-minha-delpi-ai-api python scripts/sync_api_pac_quality_openapi.py"
echo ""
echo "[OK] post_deploy_verify"
