# Subdomínio Cloudflare — `pac-api.minhadelpi.com.br`

Guia para expor a **API PAC Qualidade** na internet, integrada ao agente GPT da Minha DELPI.

**URL pública alvo:** `https://pac-api.minhadelpi.com.br`

---

## Visão geral

```
Internet
   │
   ▼
Cloudflare (TLS + proxy)
   │
   ▼
cloudflared (srv-api) ──► localhost:8082 ──► api-pac-quality-nginx ──► api-pac-quality:8010
```

No **srv-api**, a porta **80** já é do `delpi-gateway` (stack DELPI). A API PAC usa **nginx próprio** em outra porta (`NGINX_HTTP_PORT=8082` no `.env`). O **Cloudflare Tunnel** (`cloudflared`) roteia o subdomínio para essa porta.

Não é necessário registro DNS tipo `A` apontando IP público quando se usa tunnel — o Cloudflare cria o CNAME automaticamente.

### Desenvolvimento local (túnel quick)

Para testar o Custom GPT contra sua máquina:

```bash
cloudflared tunnel --url http://localhost:8082
```

O comando imprime uma URL `https://….trycloudflare.com` — use no builder do GPT. Essa URL **expira** quando o `cloudflared` encerra. Não confunda com `pac-api.minhadelpi.com.br` (tunnel permanente no srv-api).

---

## Pré-requisitos (servidor)

Antes de configurar o Cloudflare:

1. Stack PAC no ar:

   ```bash
   cd ~/projetos/api-pac-quality
   cp .env.srv-api.example .env
   # preencher PLUGINS_DB_PASSWORD (copiar do delpi-central/infra/.env)
   cp docker-compose.override.srv-api.example.yml docker-compose.override.yml
   docker compose up -d --build
   ```

2. Health local OK:

   ```bash
   curl -s http://localhost:8082/health
   ```

   Esperado: `"status":"ok"`, `"api_delpi_delegation":"configured"` e `"core_api_directory":"configured"` (com api-delpi e Core API no `.env`).

3. Porta livre (se mudar de 8082):

   ```bash
   ss -tlnp | grep ':8082 '
   ```

---

## Passo 1 — Cloudflare Zero Trust (Tunnel)

O srv-api já roda o container `cloudflared`. Você só adiciona um **Public Hostname** novo ao tunnel existente.

### Pelo dashboard (recomendado)

1. Acesse [Cloudflare Zero Trust](https://one.dash.cloudflare.com/)
2. Menu **Networks** → **Tunnels**
3. Abra o tunnel já usado pelo srv-api (o que atende `minhadelpi.com.br` hoje)
4. Aba **Public Hostname** → **Add a public hostname**
5. Preencha:

   | Campo | Valor |
   |-------|--------|
   | **Subdomain** | `pac-api` |
   | **Domain** | `minhadelpi.com.br` |
   | **Path** | *(vazio)* |
   | **Type** | `HTTP` |
   | **URL** | `localhost:8082` |

6. Salve

O Cloudflare cria automaticamente o registro DNS `pac-api.minhadelpi.com.br` → tunnel.

### Pelo arquivo de config (alternativa)

Se o tunnel usa `config.yml` no host, adicione em `ingress`:

```yaml
ingress:
  # ... hostnames existentes ...

  - hostname: pac-api.minhadelpi.com.br
    service: http://localhost:8082

  - service: http_status:404
```

Reinicie o cloudflared:

```bash
docker restart cloudflared
# ou o nome exato do container: docker ps | grep cloudflared
```

---

## Passo 2 — SSL/TLS

No painel Cloudflare → domínio **minhadelpi.com.br** → **SSL/TLS**:

| Configuração | Valor recomendado |
|--------------|-------------------|
| Modo de criptografia | **Full** ou **Full (strict)** |
| Always Use HTTPS | **On** (opcional, recomendado) |

O origin (nginx da api-pac) recebe HTTP em `8082`; o TLS termina no Cloudflare.

---

## Passo 3 — Validar subdomínio

```bash
# No srv-api
curl -s http://localhost:8082/health

# De qualquer máquina (após DNS propagar — geralmente minutos)
curl -s https://pac-api.minhadelpi.com.br/health
curl -s -o /dev/null -w "%{http_code}\n" https://pac-api.minhadelpi.com.br/docs
```

Resposta `/health` esperada:

```json
{
  "status": "ok",
  "service": "api-pac-quality",
  "plugins_database": "ok",
  "api_delpi_delegation": "configured",
  "core_api_directory": "configured"
}
```

### Teste autenticado (opcional)

Com `PAC_QUALITY_API_KEY` (mesmo valor do `.env` e do Custom GPT):

```bash
curl -s -H "Authorization: Bearer $PAC_QUALITY_API_KEY" \
  "https://pac-api.minhadelpi.com.br/quality/action-plans/assignable-users?q=ana&limit=5"
```

---

## Passo 4 — Variáveis no `.env` da API PAC

Confirme no `~/projetos/api-pac-quality/.env`:

```env
PUBLIC_BASE_URL=https://pac-api.minhadelpi.com.br
NGINX_HTTP_PORT=8082
API_PAC_ROOT_PATH=
API_DELPI_BASE_URL=http://delpi-api-delpi:8000
API_DELPI_INTERNAL_SERVICE_TOKEN=<delpi-central/infra/.env>
CORE_API_BASE_URL=http://delpi-core-api:8000
CORE_API_INTEGRATIONS_SERVICE_TOKEN=<delpi-central/infra/.env>
PAC_QUALITY_API_KEY=<openssl rand -hex 32>
```

Se alterar `NGINX_HTTP_PORT`, atualize também a URL no tunnel (`localhost:PORT`).

---

## Passo 5 — Agente GPT (Minha DELPI)

Após o subdomínio responder:

### 5.1 Provider OpenAPI

Na UI **Actions do agente** ou API admin do chat:

```json
{
  "providerKey": "api-pac-quality",
  "name": "API PAC Qualidade",
  "type": "openapi",
  "baseUrl": "https://pac-api.minhadelpi.com.br",
  "authMode": "user_token",
  "allowRead": true,
  "allowWrite": true,
  "allowAdmin": false,
  "requiresConfirmationForWrite": true
}
```

Schema: `https://pac-api.minhadelpi.com.br/openapi.json`

### 5.2 Sincronizar actions no chat

```bash
docker exec delpi-minha-delpi-ai-api python scripts/sync_api_pac_quality_openapi.py
```

### 5.3 Configurar GPT Customizado (ChatGPT workspace)

Prompt, descrição, quebra-gelos e checklist: **[chatgpt-especialista-qualidade.md](chatgpt-especialista-qualidade.md)**.

Autenticação das Actions: **[chatgpt-acoes-api-key.md](chatgpt-acoes-api-key.md)**.

### 5.4 Permissões RBAC

Se ainda não registrou o manifesto do plugin:

```bash
cd ~/projetos/delpi-central
TOKEN="<jwt-admin>" ./plugins/quality-action-plans/scripts/register-manifest.sh
```

Vincule `quality-action-plans.read` e `quality-action-plans.write` aos grupos/roles dos analistas de qualidade.

---

## Alternativa: DNS tipo A (sem tunnel)

Use **somente** se o srv-api tiver IP público direto e **não** usar cloudflared para este host:

| Tipo | Nome | Conteúdo | Proxy |
|------|------|----------|-------|
| `A` | `pac-api` | IP público do srv-api | Proxied (laranja) |

Nesse caso, o origin precisa escutar na porta que o Cloudflare alcança (80/443). No srv-api a porta 80 está ocupada — **prefira o tunnel** com `localhost:8082`.

---

## Troubleshooting

| Sintoma | Causa provável | Ação |
|---------|----------------|------|
| `522` / timeout | Tunnel não aponta para `8082` ou stack parada | `docker compose ps` + conferir Public Hostname |
| `502` | nginx up, API down | `docker compose logs api-pac-quality` |
| `plugins_database: unavailable` | Rede Docker / credenciais Postgres | `docker-compose.override.yml` + `PLUGINS_DB_*` |
| `401` nas rotas | `PAC_QUALITY_API_KEY` ausente ou errada | Bearer ou `X-Api-Key` no curl/GPT |
| `503` em assignable-users | Core API não configurada | `CORE_API_BASE_URL` + `CORE_API_INTEGRATIONS_SERVICE_TOKEN` |
| `api_delpi_delegation: misconfigured` | Token ou URL api-delpi | Copiar `API_DELPI_INTERNAL_SERVICE_TOKEN` do infra |
| Health OK local, falha no HTTPS | Tunnel/DNS ainda não propagou | Aguardar 2–5 min; conferir hostname no Zero Trust |

---

## Checklist completo

- [ ] Migrations `quality-action-plans` aplicadas (`V001`–`V019`)
- [ ] `.env` preenchido (delegação + Core API + `PAC_QUALITY_API_KEY`)
- [ ] `docker-compose.override.yml` na rede `infra_delpi-network`
- [ ] `curl http://localhost:8082/health` → OK (`api_delpi_delegation`, `core_api_directory`)
- [ ] `bash scripts/smoke_pac_delpi_delegation.sh` (opcional)
- [ ] Public Hostname `pac-api.minhadelpi.com.br` → `http://localhost:8082` no tunnel
- [ ] `curl https://pac-api.minhadelpi.com.br/health` → OK
- [ ] Provider `api-pac-quality` no agente com `baseUrl` do subdomínio
- [ ] `sync_api_pac_quality_openapi.py` executado
- [ ] Manifesto RBAC registrado

Ver também: [DEPLOYMENT.md](DEPLOYMENT.md)
