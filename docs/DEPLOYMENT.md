# Deploy — API PAC Qualidade

Stack **autônoma**: API FastAPI + **nginx próprio** neste repositório. Não passa pelo gateway `delpi-central`.

Consumida pelo **agente GPT** da Minha DELPI via provider OpenAPI (`api-pac-quality`).

## Estrutura

```
api-pac-quality/
  Dockerfile              # API (uvicorn :8010)
  docker-compose.yml      # api-pac-quality + nginx
  nginx/
    Dockerfile
    nginx.conf            # pac-api.minhadelpi.com.br → api:8010
  docs/
    openapi-snapshot-chat.json
```

| Serviço | Container | Porta exposta |
|---------|-----------|---------------|
| API | `api-pac-quality` | interna `8010` |
| Nginx | `api-pac-quality-nginx` | `80` (host) |

## Build

Contexto de build = pasta pai `projetos/` (irmãos `api-pac-quality` + `delpi-central/shared`).

```bash
cd /caminho/projetos
docker build -f api-pac-quality/Dockerfile -t api-pac-quality:latest .
docker build -f api-pac-quality/nginx/Dockerfile -t api-pac-quality-nginx:latest api-pac-quality/nginx
```

## Subir no servidor

```bash
cd api-pac-quality
cp .env.example .env
# Preencher PLUGINS_DB_*, Keycloak, CORE_API_URL (URL pública da Minha DELPI)

docker compose up -d --build
curl -s http://localhost/health
```

## Subdomínio Cloudflare

**URL pública:** `https://pac-api.minhadelpi.com.br`

### DNS

| Tipo | Nome | Conteúdo | Proxy |
|------|------|----------|-------|
| `A` | `pac-api` | IP do servidor desta stack | Proxied |

Aponte o registro para o **servidor onde roda este docker compose** (não o gateway principal da Minha DELPI).

### SSL

- Cloudflare termina TLS no edge.
- Origin recebe HTTP na porta `80` com `X-Forwarded-Proto: https`.
- Modo recomendado: **Full** ou **Full (strict)**.

### Nginx

Configuração em `nginx/nginx.conf` — `server_name pac-api.minhadelpi.com.br`.

Para outro hostname, edite `nginx/nginx.conf` e rebuild:

```bash
docker compose build nginx && docker compose up -d nginx
```

## Variáveis (`.env`)

| Variável | Exemplo | Descrição |
|----------|---------|-----------|
| `NGINX_HTTP_PORT` | `80` | Porta HTTP publicada no host |
| `PUBLIC_BASE_URL` | `https://pac-api.minhadelpi.com.br` | CORS + documentação |
| `API_PAC_ROOT_PATH` | *(vazio)* | Sem prefixo — nginx na raiz |
| `PLUGINS_DB_*` | — | PostgreSQL schema `quality` (mesmo banco plugins DELPI) |
| `KEYCLOAK_*` | URLs públicas Minha DELPI | JWT `delpi-auth` |
| `CORE_API_URL` | `https://www.minhadelpi.com.br/core-api` | Validação RBAC remota |

## Migrations (banco)

Executadas na stack DELPI (`delpi-central/api-delpi`):

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

Schema: `docs/openapi-snapshot-chat.json`

```bash
docker exec delpi-minha-delpi-ai-api python scripts/sync_api_pac_quality_openapi.py \
  --from-file /caminho/api-pac-quality/docs/openapi-snapshot-chat.json
```

Permissões: `quality-action-plans.read`, `quality-action-plans.write` (manifesto em `delpi-central/plugins/quality-action-plans/`).

## Testes

```bash
pytest tests/ -q
```

## Checklist produção

1. Migrations `quality-action-plans` aplicadas (`V001`–`V003`)
2. `curl https://pac-api.minhadelpi.com.br/health` → `plugins_database: ok`
3. DNS Cloudflare `pac-api` → IP deste servidor
4. `.env` com `CORE_API_URL` e Keycloak apontando para produção DELPI
5. Provider `api-pac-quality` no agente com `baseUrl` do subdomínio
6. `sync_api_pac_quality_openapi.py` após mudanças de rotas
