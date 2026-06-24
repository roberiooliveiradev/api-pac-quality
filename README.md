# API PAC Qualidade DELPI

API transacional de **planos de ação central de qualidade** (PAC). Usada pelo agente GPT de causa raiz para escrita, histórico e inteligência operacional.

Consultas consolidadas para liderança (plugin) serão expostas pela **api-delpi** (Fase 4 do playbook).

## Arquitetura

| Camada | Repositório | Responsabilidade |
|--------|-------------|------------------|
| API transacional | `api-pac-quality` (este repo) | CRUD, Ishikawa, 5 Porquês, ações, knowledge layer |
| Migrations + PostgreSQL | `delpi-central/api-delpi/migrations/plugins/quality-action-plans/` | Schema `quality.*` no banco de plugins |
| Leitura agregada | `delpi-central/api-delpi` | Dashboards do plugin `quality-action-plans` |
| Agente | `delpi-central/minha-delpi-ai-api` | Conversa + chamadas à API PAC |

O banco é o **mesmo PostgreSQL de plugins** da Minha DELPI (`PLUGINS_DB_*`), no schema `quality`.

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

## Desenvolvimento local

```bash
cd api-pac-quality
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ../delpi-central/shared[fastapi]

cp .env.example .env
# preencher PLUGINS_DB_* e Keycloak

python -m uvicorn app.asgi:application --reload --port 8010
```

Swagger: `http://localhost:8010/docs`

## Docker (stack DELPI)

O serviço está no `docker-compose` com gateway em `/apps/api-pac-quality`:

```bash
cd delpi-central/infra
docker compose -f docker-compose.dev.yml up -d api-pac-quality
```

Build context: raiz `projetos/` (irmãos `delpi-central` e `api-pac-quality`).

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
| `PATCH` | `/quality/action-plans/{id}/status` | Atualizar status |
| `PUT` | `/quality/action-plans/{id}/ishikawa` | Registrar Ishikawa |
| `PUT` | `/quality/action-plans/{id}/five-whys` | Registrar 5 Porquês |
| `POST` | `/quality/action-plans/{id}/actions` | Criar ações |
| `PATCH` | `/quality/action-plans/{id}/actions/{action_id}` | Atualizar ação |
| `POST` | `/quality/action-plans/{id}/effectiveness-review` | Verificação de eficácia |

### Leitura consolidada (api-delpi — plugin)

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/quality/action-plans/dashboard` | Cards executivos |
| `GET` | `/quality/action-plans` | Listagem |
| `GET` | `/quality/action-plans/overdue` | Planos com ações atrasadas |
| `GET` | `/quality/action-plans/{id}` | Detalhe completo |

Envelope de resposta (padrão api-delpi): `{ success, message, data, error }`.

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

## Próximos passos (playbook)

1. ~~Knowledge layer simples~~ (Fase 2 — MVP textual)
2. Agente GPT + gateway (`minha-delpi-ai-api`)

Documentação completa: `playbook_pac_qualidade_delpi.md`.
