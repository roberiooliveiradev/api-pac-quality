# Contrato HTTP api-pac-quality ↔ api-delpi

Delegação **server-to-server (S2S)** das operações transacionais do analista GPT. A **api-pac** continua sendo a fachada pública (`pac_*` no OpenAPI); a **api-delpi** permanece fonte de verdade do CRUD em `/quality/action-plans`.

## Papéis

| Serviço | Papel |
|---------|--------|
| **api-pac-quality** | Auth GPT (`PAC_QUALITY_API_KEY`), OpenAPI `pac_*`, inteligência local (similaridade, sugestões) |
| **api-delpi** | Persistência, regras de negócio, auditoria, RBAC interno (bypass S2S) |

## Ativação

```env
PAC_DELEGATE_TRANSACTIONAL_TO_API_DELPI=true
API_DELPI_BASE_URL=http://api-delpi:8000
API_DELPI_INTERNAL_SERVICE_TOKEN=<mesmo token do delpi-central>
API_DELPI_TIMEOUT_SECONDS=60
```

Com a flag `false` (padrão) ou sem URL/token, a api-pac usa o repositório Postgres local (comportamento legado).

## Autenticação S2S

A api-pac envia em toda chamada delegada:

| Header | Valor |
|--------|--------|
| `X-Delpi-Service-Token` | `API_DELPI_INTERNAL_SERVICE_TOKEN` |
| `Authorization` | `Bearer <token>` (se não houver outro) |
| `X-Delpi-Caller-App` | `api-pac-quality` |
| `X-Delpi-Actor-Id` | `pac-gpt-agent` |
| `X-Delpi-Actor-Name` | `Agente GPT PAC` |

A api-delpi valida via `delpi_auth` (`internal-service`, `is_superadmin=true`).

### Auditoria do ator

Middleware `pac_service_actor_middleware` na api-delpi substitui o usuário `internal-service` pelo ator dos headers `X-Delpi-Actor-*` em rotas `/quality/action-plans/*`, preservando `created_by` / `updated_by` / `uploaded_by` como `pac-gpt-agent`.

## Envelope de resposta

- **Entrada:** corpo/query idênticos ao contrato api-delpi (mesmos paths sob `/quality/action-plans`).
- **Saída:** envelope `{ success, message, data, error, meta? }` inalterado.
- **meta.operationId:** reescrito de `create_quality_action_plan` → `pac_create_action_plan` (mapa em `pac_delpi_operation_mapping.py`).

Erros de indisponibilidade da api-delpi: HTTP 503, `error.code = API_DELPI_UNAVAILABLE`.

## Operações delegadas

### Leitura (analista)

| Método | Path api-delpi | operationId delpi | operationId pac |
|--------|----------------|-------------------|-----------------|
| GET | `/quality/action-plans` | `list_quality_action_plans` | `pac_list_action_plans` |
| GET | `/quality/action-plans/{id}` | `get_quality_action_plan_detail` | `pac_get_action_plan` |
| GET | `.../evidences` | `list_quality_action_plan_evidences` | `pac_list_plan_evidences` |
| GET | `.../export/rnc-8d` | `export_quality_action_plan_rnc_8d` | `pac_export_rnc_8d` |
| GET | `.../evidences/{ev_id}/file` | — (binário) | `pac_download_plan_evidence` |

### Escrita (analista)

| Método | Path (sufixo) | delpi → pac |
|--------|---------------|-------------|
| POST | `` | `create_quality_action_plan` → `pac_create_action_plan` |
| PATCH | `/{id}` | `update_quality_action_plan` → `pac_update_action_plan` |
| PATCH | `/{id}/status` | `update_quality_action_plan_status` → `pac_update_action_plan_status` |
| POST | `/{id}/reopen` | `reopen_quality_action_plan` → `pac_reopen_action_plan` |
| PUT | `/{id}/ishikawa` | `upsert_quality_action_plan_ishikawa` → `pac_upsert_ishikawa` |
| PUT | `/{id}/five-whys` | `upsert_quality_action_plan_five_whys` → `pac_upsert_five_whys` |
| POST | `/{id}/actions` | `create_quality_action_plan_actions` → `pac_create_plan_actions` |
| PATCH | `/{id}/actions/{aid}` | `update_quality_action_plan_action` → `pac_update_plan_action` |
| DELETE | `/{id}/actions/{aid}` | `delete_quality_action_plan_action` → `pac_delete_plan_action` |
| POST | `/{id}/effectiveness-review` | `record_quality_action_plan_effectiveness` → `pac_record_effectiveness_review` |
| POST | `.../effectiveness-review/submit` | `submit_quality_action_plan_effectiveness_review` → `pac_submit_effectiveness_review` |
| PUT | `/{id}/rnc-8d` | `upsert_quality_action_plan_rnc_8d` → `pac_upsert_rnc_8d` |
| POST | `/{id}/evidences` | `attach_quality_action_plan_evidence` → `pac_attach_plan_evidence` (multipart) |
| DELETE | `/{id}/evidences/{eid}` | `delete_quality_action_plan_evidence` → `pac_delete_plan_evidence` |

## Não delegado (permanece na api-pac)

- Auth middleware GPT
- `pac_search_similar_cases`, `pac_search_solution_patterns`, `pac_suggest_actions`
- Health, OpenAPI público
- Operações só do plugin: aprovar/rejeitar eficácia, dashboard, minha fila, audit log, etc.

## Implementação

```
quality_action_plans_router
  → pac_delpi_route_delegate (se flag ativa)
  → PacApiDelpiDelegationService
  → ApiDelpiQualityGateway (httpx)
  → api-delpi /quality/action-plans/*
```

## Homologação

1. Subir delpi-central com `API_DELPI_INTERNAL_SERVICE_TOKEN` definido.
2. api-pac na rede `infra_delpi-network` com override srv-api.
3. `PAC_DELEGATE_TRANSACTIONAL_TO_API_DELPI=true`
4. Criar plano via GPT (api-pac) e conferir registro no plugin (api-delpi).
5. `pytest tests/unit/test_pac_delpi_*_parity.py tests/unit/test_pac_api_delpi_delegation.py`

## Referências

- Paridade: `tests/unit/test_pac_delpi_read_parity.py`, `test_pac_delpi_write_parity.py`
- Gateway: `app/infrastructure/gateways/api_delpi_quality_gateway.py`
- Middleware ator: `api-delpi/app/middleware/pac_service_actor_middleware.py`
