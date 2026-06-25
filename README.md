# API PAC Qualidade DELPI

API transacional de **planos de ação central de qualidade** (PAC). Usada pelo agente GPT de causa raiz para escrita, histórico e inteligência operacional.

Consultas consolidadas e **CRUD do plugin MFE** são expostos pela **api-delpi** (`/apps/api-delpi/quality/action-plans/*`). Esta API permanece dedicada ao **agente GPT** (Actions + API key) e à **camada de inteligência** (casos similares, padrões de solução).

## Arquitetura

| Camada | Repositório | Responsabilidade |
|--------|-------------|------------------|
| **Plugin MFE + api-delpi** | `delpi-central` | CRUD e leitura via JWT (`quality-action-plans` caller) |
| **API transacional GPT** | `api-pac-quality` (este repo) | Mesmos endpoints de escrita + inteligência; auth JWT ou `PAC_QUALITY_API_KEY` |
| **Migrations + PostgreSQL** | `delpi-central/api-delpi/migrations/plugins/quality-action-plans/` | Schema `quality.*` (V001–V007) |
| **Agente ChatGPT** | Custom GPT + Actions | OpenAPI desta API em `pac-api.minhadelpi.com.br` |
| **Agente Minha DELPI** (roadmap) | `minha-delpi-ai-api` | Provider OpenAPI sync |

O banco é o **mesmo PostgreSQL de plugins** da Minha DELPI (`PLUGINS_DB_*`), no schema `quality`.

**Deploy:** stack autônoma com nginx próprio — ver [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). Subdomínio Cloudflare: [docs/cloudflare-subdominio-pac-api.md](docs/cloudflare-subdominio-pac-api.md). Não faz parte do gateway `delpi-central`.

## Pré-requisitos

1. Migrations do plugin `quality` já aplicadas (sequências e `quality.submodules`).
2. SDK `delpi-auth` instalado (`pip install -e ../delpi-central/shared[fastapi]`).
3. Variáveis `PLUGINS_DB_*` e Keycloak configuradas (ver `.env.example`).

## Migrations (delpi-central)

```bash
cd delpi-central/api-delpi

# Status
python scripts/run_plugins_migrations.py status --plugin quality-action-plans

# Aplicar
python scripts/run_plugins_migrations.py up --plugin quality-action-plans
```

No Docker (stack `infra/`):

```bash
docker exec delpi-api-delpi python scripts/run_plugins_migrations.py up --plugin quality-action-plans
```

Arquivos:

- `V001__create_pac_action_plans_core.sql` — tabelas principais
- `V002__seed_pac_sequences_and_submodule.sql` — sequência `PAC-YYYY-####` e submódulo `action_plans`

## Desenvolvimento e homologação local

**Não** é necessário subir container desta API no dev. O plugin e os testes de Onda 1 usam a **api-delpi** (`delpi-central`, container `delpi-api-delpi`):

```bash
cd delpi-central/infra
docker compose -f docker-compose.dev.yml up -d --force-recreate api-delpi quality-action-plans
bash ../api-delpi/scripts/deploy_rnc_8d_template.sh
export TOKEN="<jwt>" && python3 ../scripts/homologacao/run_h1_api_smoke.py
```

Testes unitários deste repo (`pytest tests/ -q`) validam paridade de `operation_id` com a api-delpi.

### Uvicorn local (opcional — debug pontual)

```bash
cd api-pac-quality
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ../delpi-central/shared[fastapi]

cp .env.example .env
# PLUGINS_DB_* ← mesmos valores de delpi-central/infra/.env (host localhost:5433 se Postgres exposto)

python -m uvicorn app.asgi:application --reload --port 8010
```

Swagger: `http://localhost:8010/docs`

## Docker (somente srv-api / produção)

```bash
cd api-pac-quality
cp .env.srv-api.example .env
# PLUGINS_DB_PASSWORD ← copiar de delpi-central/infra/.env
cp docker-compose.override.srv-api.example.yml docker-compose.override.yml
docker compose up -d --build
curl -s http://localhost:8082/health
```

| Recurso | Caminho |
|---------|---------|
| Deploy geral | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |
| **Subdomínio Cloudflare** | [docs/cloudflare-subdominio-pac-api.md](docs/cloudflare-subdominio-pac-api.md) |
| **ChatGPT Actions (API Key)** | [docs/chatgpt-acoes-api-key.md](docs/chatgpt-acoes-api-key.md) |
| **GPT Especialista Qualidade** | [docs/chatgpt-especialista-qualidade.md](docs/chatgpt-especialista-qualidade.md) |
| OpenAPI agente GPT | `GET /openapi.json` — 24 operações (fluxo analista, ≤30 ChatGPT) |

Documentação: [docs/openapi-analista-24-operacoes.md](docs/openapi-analista-24-operacoes.md)
| `.env` produção | [.env.srv-api.example](.env.srv-api.example) |

Build context: raiz `projetos/` (irmãos `api-pac-quality` + `delpi-central/shared`).

## Permissões (Core API)

Registrar manifesto do plugin (cria permissões RBAC):

```bash
TOKEN="<jwt-admin>" ./plugins/quality-action-plans/scripts/register-manifest.sh
```

Códigos: `quality-action-plans.read`, `quality-action-plans.write`, `quality-action-plans.manage`, `api-delpi.quality.action-plans.read`.

## Endpoints (Fase 1 — MVP)

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/quality/action-plans` | Criar plano |
| `GET` | `/quality/action-plans` | Listar com filtros |
| `GET` | `/quality/action-plans/{id}` | Detalhe |
| `PATCH` | `/quality/action-plans/{id}` | Atualizar identificação do plano |
| `PATCH` | `/quality/action-plans/{id}/status` | Atualizar status |
| `PUT` | `/quality/action-plans/{id}/ishikawa` | Registrar Ishikawa |
| `PUT` | `/quality/action-plans/{id}/five-whys` | Registrar 5 Porquês |
| `POST` | `/quality/action-plans/{id}/actions` | Criar ações |
| `PATCH` | `/quality/action-plans/{id}/actions/{action_id}` | Atualizar ação |
| `POST` | `/quality/action-plans/{id}/effectiveness-review` | Verificação de eficácia |
| `PUT` | `/quality/action-plans/{id}/rnc-8d` | Relatório 8D |
| `GET` | `/quality/action-plans/{id}/export/rnc-8d` | Export Excel (com imagens na aba Anexos) |
| `GET/POST/DELETE` | `/quality/action-plans/{id}/evidences` | Evidências (`action_id` opcional no upload) |

### Leitura e CRUD — plugin (api-delpi)

Implementado em `delpi-central/api-delpi`. O MFE **não** chama esta API diretamente.

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/quality/action-plans/dashboard` | Cards executivos |
| `GET` | `/quality/action-plans` | Listagem |
| `GET` | `/quality/action-plans/overdue` | Planos com ações atrasadas |
| `GET` | `/quality/action-plans/{id}` | Detalhe completo |
| `PATCH` | `/quality/action-plans/{id}` | Atualizar identificação |
| `POST` | `/quality/action-plans` | Criar plano |
| `PATCH` | `/quality/action-plans/{id}/status` | Atualizar status |
| `PUT` | `/quality/action-plans/{id}/ishikawa` | Ishikawa |
| `PUT` | `/quality/action-plans/{id}/five-whys` | 5 Porquês |
| `POST` | `/quality/action-plans/{id}/actions` | Criar ações |
| `PATCH` | `/quality/action-plans/{id}/actions/{action_id}` | Atualizar ação |
| `POST` | `/quality/action-plans/{id}/effectiveness-review` | Eficácia |

Doc: `delpi-central/api-delpi/docs/api/quality-action-plans-pac.md`

Envelope de resposta (padrão api-delpi): `{ success, message, data, error }`.

## Endpoints desta API (agente GPT + inteligência)

### Escrita (paridade com api-delpi)

## Testes

```bash
pytest tests/ -q
```

## Endpoints de inteligência (Fase 2 — Knowledge Layer)

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/quality/action-plans/intelligence/similar-cases` | Casos similares + recorrência |
| `POST` | `/quality/action-plans/intelligence/solution-patterns/search` | Padrões de solução testados |
| `POST` | `/quality/action-plans/intelligence/suggest-actions` | Sugestões com base histórica |

O índice de similaridade é atualizado automaticamente ao criar plano, registrar 5 Porquês e revisar eficácia. Padrões de solução são gerados quando a eficácia é `effective` ou `partially_effective`.

Migration: `V003__create_pac_knowledge_layer.sql` (tabelas + `pg_trgm`).

## Roadmap e excelência

| Documento | Repositório | Conteúdo |
|---|---|---|
| `docs/12-roadmap-e-evolucao/quality-action-plans/PLAYBOOK-EXCELENCIA.md` | delpi-central | North star, ondas 0–7, métricas, priorização 90 dias |
| `docs/12-roadmap-e-evolucao/quality-action-plans/status-atual.md` | delpi-central | Snapshot do que está implementado |
| `docs/12-roadmap-e-evolucao/quality-action-plans/HOMOLOGACAO.md` | delpi-central | Roteiro de homologação |
| `playbook_pac_qualidade_delpi.md` | api-pac-quality | Especificação funcional v0.1 |

**Próxima onda (Onda 1):** homologar H1–H3 na **api-delpi** + plugin; deploy api-pac em produção para o GPT.
