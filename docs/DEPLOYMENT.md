# Deploy — API PAC Qualidade

Stack **autônoma**: API FastAPI + **nginx próprio** neste repositório. Não passa pelo gateway `delpi-central`.

Consumida pelo **agente GPT** da Minha DELPI via provider OpenAPI (`api-pac-quality`).

## Documentação

| Documento | Conteúdo |
|-----------|----------|
| [contrato-http-api-pac-api-delpi.md](contrato-http-api-pac-api-delpi.md) | Delegação CRUD → api-delpi (S2S) |
| [chatgpt-acoes-api-key.md](chatgpt-acoes-api-key.md) | **ChatGPT Custom GPT** — chave API Bearer |
| [autenticacao-api-pac.md](autenticacao-api-pac.md) | **Autenticação** — só `PAC_QUALITY_API_KEY` (sem delpi_auth) |
| [chatgpt-especialista-qualidade.md](chatgpt-especialista-qualidade.md) | **Prompt, descrição e quebra-gelos** do agente |
| `GET /openapi.json` | Contrato OpenAPI do agente GPT (**26 operações** — fluxo analista) |

Ver [openapi-analista-24-operacoes.md](openapi-analista-24-operacoes.md).
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
    chatgpt-acoes-api-key.md
```

| Serviço | Container | Porta no host |
|---------|-----------|---------------|
| API | `api-pac-quality` | interna `8010` (sem publish) |
| Nginx | `api-pac-quality-nginx` | `NGINX_HTTP_PORT` (ex.: `8082` no srv-api) |

## Build

Contexto de build = pasta pai `projetos/` (`api-pac-quality/Dockerfile` — sem dependência de `delpi-central/shared`).

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
| `PAC_QUALITY_API_KEY` | `openssl rand -hex 32` | Auth ChatGPT Actions |
| `API_DELPI_BASE_URL` | `http://delpi-api-delpi:8000` | CRUD transacional via api-delpi S2S (obrigatório) |
| `API_DELPI_INTERNAL_SERVICE_TOKEN` | copiar de `delpi-central/infra/.env` | Token S2S api-delpi |
| `CORE_API_BASE_URL` ou `CORE_API_URL` | `http://delpi-core-api:8000` (Docker) ou URL pública | Diretório assignable users |
| `CORE_API_INTEGRATIONS_SERVICE_TOKEN` | copiar de `delpi-central/infra/.env` | Token S2S Core API |
| `KEYCLOAK_*` | URLs `https://minhadelpi.com.br/auth/...` | Legado — **não** usado em runtime (só API key) |

## Health

```bash
curl -s http://localhost:8082/health | jq .
```

Resposta esperada:

```json
{
  "status": "ok",
  "service": "api-pac-quality",
  "plugins_database": "ok",
  "api_delpi_delegation": "configured",
  "core_api_directory": "configured"
}
```

| Campo | Valores | Significado |
|-------|---------|-------------|
| `status` | `ok` \| `degraded` | `ok` se Postgres OK **ou** delegação habilitada |
| `plugins_database` | `ok` \| `unavailable` | Conexão direta ao Postgres (modo sem delegação) |
| `api_delpi_delegation` | `configured` \| `misconfigured` | CRUD S2S → api-delpi (obrigatório em produção) |
| `core_api_directory` | `configured` \| `not_configured` | `pac_search_assignable_users` |

Smoke delegação: `bash scripts/smoke_pac_delpi_delegation.sh`

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
docker exec delpi-minha-delpi-ai-api python scripts/sync_api_pac_quality_openapi.py
```

O script importa de `https://pac-api.minhadelpi.com.br/openapi.json` por padrão.

## Testes

```bash
pytest tests/ -q
./scripts/ci-smoke.sh
```

## Checklist produção

1. Migrations `quality-action-plans` (**V001`–`V019`**) no Postgres `plugins_hub`
2. Template 8D: `bash ../delpi-central/api-delpi/scripts/deploy_rnc_8d_template.sh` no srv-api (ou copiar xlsx para volume PAC)
3. Stack PAC + override de rede Docker + vars delegação/Core API no `.env`
4. `docker compose up -d --build` (rebuild obrigatório após rotas novas)
5. `curl http://localhost:8082/health` → `api_delpi_delegation: configured`, `core_api_directory: configured`
6. `bash scripts/post_deploy_verify.sh` (ou `../delpi-central/scripts/homologacao/check-pac-api-server.sh`)
7. Subdomínio Cloudflare → `curl https://pac-api.minhadelpi.com.br/health` → OK
8. OpenAPI com **26 operações** (`audit_pac_openapi_operation_limit.py --check`)
9. `python3 ../delpi-central/scripts/homologacao/run_h2_pac_api_smoke.py` (homologação H2)
10. `docker exec delpi-minha-delpi-ai-api python scripts/sync_api_pac_quality_openapi.py --check-onda1`
11. Manifesto RBAC `quality-action-plans`

### Deploy rápido (srv-api)

```bash
cd ~/projetos/api-pac-quality
git pull
docker compose up -d --build
bash scripts/post_deploy_verify.sh
```
