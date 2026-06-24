# Deploy — API PAC Qualidade

Stack **autônoma**: API FastAPI + **nginx próprio** neste repositório. Não passa pelo gateway `delpi-central`.

Consumida pelo **agente GPT** da Minha DELPI via provider OpenAPI (`api-pac-quality`).

## Documentação

| Documento | Conteúdo |
|-----------|----------|
| [cloudflare-subdominio-pac-api.md](cloudflare-subdominio-pac-api.md) | **Subdomínio Cloudflare + tunnel** (passo a passo) |
| [openapi-snapshot-chat.json](openapi-snapshot-chat.json) | Contrato OpenAPI para o agente GPT |
| `../.env.srv-api.example` | `.env` de produção para o srv-api |
| `../docker-compose.override.srv-api.example.yml` | Rede Docker com `delpi-central` |

## Estrutura

```
api-pac-quality/
  Dockerfile              # API (uvicorn :8010)
  docker-compose.yml      # api-pac-quality + nginx
  nginx/
    Dockerfile
    nginx.conf            # pac-api.minhadelpi.com.br → api:8010
  docs/
    cloudflare-subdominio-pac-api.md
    openapi-snapshot-chat.json
```

| Serviço | Container | Porta no host |
|---------|-----------|---------------|
| API | `api-pac-quality` | interna `8010` (sem publish) |
| Nginx | `api-pac-quality-nginx` | `NGINX_HTTP_PORT` (ex.: `8082` no srv-api) |

## Build

Contexto de build = pasta pai `projetos/` (irmãos `api-pac-quality` + `delpi-central/shared`).

```bash
cd /caminho/projetos
docker build -f api-pac-quality/Dockerfile -t api-pac-quality:latest .
```

## Subir no srv-api (produção)

```bash
cd ~/projetos/api-pac-quality
cp .env.srv-api.example .env
grep '^PLUGINS_DB_PASSWORD=' ~/projetos/delpi-central/infra/.env   # colar no .env
cp docker-compose.override.srv-api.example.yml docker-compose.override.yml

docker compose up -d --build
curl -s http://localhost:8082/health
```

### Portas no srv-api

| Porta host | Uso |
|------------|-----|
| `80` | `delpi-gateway` — **não** usar para api-pac |
| `8010` | Outro processo no host — api-pac usa 8010 **só na rede Docker** |
| `8082` | Nginx da api-pac (`NGINX_HTTP_PORT`) — roteado pelo cloudflared |

Verificar portas: `ss -tlnp | grep -E ':80 |:8082 '`

## Subdomínio Cloudflare

**URL pública:** `https://pac-api.minhadelpi.com.br`

Guia completo: **[cloudflare-subdominio-pac-api.md](cloudflare-subdominio-pac-api.md)**

Resumo:

1. Subir stack local (`localhost:8082/health` OK)
2. No Zero Trust → Tunnel → **Add public hostname**: `pac-api.minhadelpi.com.br` → `http://localhost:8082`
3. Validar: `curl https://pac-api.minhadelpi.com.br/health`
4. Cadastrar provider OpenAPI no agente GPT

## Variáveis (`.env`)

Use `.env.srv-api.example` no servidor. Principais:

| Variável | srv-api | Descrição |
|----------|---------|-----------|
| `NGINX_HTTP_PORT` | `8082` | Porta HTTP do nginx no host |
| `PUBLIC_BASE_URL` | `https://pac-api.minhadelpi.com.br` | CORS + OpenAPI do agente |
| `API_PAC_ROOT_PATH` | *(vazio)* | Sem prefixo de path |
| `PLUGINS_DB_*` | igual `delpi-central/infra/.env` | Postgres `plugins_hub` |
| `KEYCLOAK_*` | URLs `https://minhadelpi.com.br/auth/...` | JWT |
| `CORE_API_URL` | `https://minhadelpi.com.br/core-api` | RBAC |

## Migrations (banco)

```bash
docker exec delpi-api-delpi python scripts/run_plugins_migrations.py up --plugin quality-action-plans
```

## Agente GPT — provider OpenAPI

```json
{
  "providerKey": "api-pac-quality",
  "name": "API PAC Qualidade",
  "type": "openapi",
  "baseUrl": "https://pac-api.minhadelpi.com.br",
  "authMode": "user_token",
  "allowRead": true,
  "allowWrite": true,
  "requiresConfirmationForWrite": true
}
```

```bash
docker exec delpi-minha-delpi-ai-api python scripts/sync_api_pac_quality_openapi.py \
  --from-file ~/projetos/api-pac-quality/docs/openapi-snapshot-chat.json
```

## Testes

```bash
pytest tests/ -q
./scripts/ci-smoke.sh
```

## Checklist produção

1. Migrations `quality-action-plans` (`V001`–`V003`)
2. Stack PAC + override de rede Docker
3. `curl http://localhost:8082/health` → `plugins_database: ok`
4. Subdomínio Cloudflare configurado (ver guia dedicado)
5. `curl https://pac-api.minhadelpi.com.br/health` → OK
6. Provider + `sync_api_pac_quality_openapi.py`
7. Manifesto RBAC `quality-action-plans`
