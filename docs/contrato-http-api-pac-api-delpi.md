# Contrato HTTP api-pac-quality ↔ api-delpi

Delegação **server-to-server (S2S)** das operações transacionais do analista GPT. A **api-pac** continua sendo a fachada pública (`pac_*` no OpenAPI); a **api-delpi** permanece fonte de verdade do CRUD em `/quality/action-plans`.

## Papéis

| Serviço | Papel |
|---------|--------|
| **api-pac-quality** | Auth GPT (`PAC_QUALITY_API_KEY`), OpenAPI `pac_*`, inteligência local (similaridade, sugestões) |
| **api-delpi** | Persistência, regras de negócio, auditoria, RBAC interno (bypass S2S) |

## Ativação (obrigatório)

A api-pac **não** persiste CRUD transacional localmente — toda rota `pac_*` de plano delega à api-delpi. Sem URL e token S2S, as Actions retornam **503** (`API_DELPI_MISCONFIGURED`).

```env
API_DELPI_BASE_URL=http://delpi-api-delpi:8000
API_DELPI_INTERNAL_SERVICE_TOKEN=<mesmo token do delpi-central>
API_DELPI_TIMEOUT_SECONDS=60
```

> A flag legada `PAC_DELEGATE_TRANSACTIONAL_TO_API_DELPI` foi removida; delegação é sempre ativa quando o gateway está configurado.

## Referência de plano (`{plan_id}`)

A api-delpi resolve **UUID** ou código **`PAC-YYYY-NNNN`** em todas as rotas com `{plan_id}` no path. A api-pac repassa o segmento inalterado (ex.: `GET /quality/action-plans/PAC-2026-0029`).

| Query / path | Comportamento |
|--------------|---------------|
| `GET /quality/action-plans/{plan_id}` | Detalhe por UUID ou código |
| `GET /quality/action-plans?code=PAC-2026-0029` | Listagem com filtro exato no campo `code` |
| `PATCH /quality/action-plans/PAC-2026-0029/...` | Escritas com código no path |

Implementação canônica: `api-delpi` → `quality_action_plan_reference_service` + `_coerce_plan_id` no repositório de leitura/escrita.

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

- **Entrada:** corpo/query idênticos ao contrato api-delpi (mesmos paths sob `/quality/action-plans`). Campos de contato V025 (`customer_contact_*`, `delpi_contact_*`) aceitos em create, PATCH e `pac_upsert_rnc_8d`.
- **Saída:** envelope `{ success, message, data, error, meta? }` inalterado. Detalhe do plano inclui `contact_roles` (papéis resolvidos cliente vs DELPI).
- **meta.operationId:** reescrito de `create_quality_action_plan` → `pac_create_action_plan` (mapa em `pac_delpi_operation_mapping.py`).

Erros de indisponibilidade da api-delpi: HTTP 503, `error.code = API_DELPI_UNAVAILABLE`.

## Operações delegadas

### Leitura (analista)

| Método | Path api-delpi | operationId delpi | operationId pac |
|--------|----------------|-------------------|-----------------|
| GET | `/quality/action-plans` | `list_quality_action_plans` | `pac_list_action_plans` |
| GET | `/quality/action-plans/{id}` | `get_quality_action_plan_detail` | `pac_get_action_plan` |
| GET | `.../evidences` | `list_quality_action_plan_evidences` | `pac_list_plan_evidences` |
| GET | `/quality/action-plans/export-templates` | `list_quality_action_plan_export_templates` | `pac_list_export_templates` |
| GET | `.../export/rnc-8d` | `export_quality_action_plan_rnc_8d` | `pac_export_rnc_8d` (`template_key` query opcional) |
| GET | `.../evidences/{ev_id}/file` | — (binário) | `pac_download_plan_evidence` |
| GET | `.../evidences/{ev_id}/content` | `get_quality_action_plan_evidence_content` | `pac_get_plan_evidence_content` |

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
| PATCH | `/{id}/evidences/{eid}` | `update_quality_action_plan_evidence` → `pac_update_plan_evidence` |
| DELETE | `/{id}/evidences/{eid}` | `delete_quality_action_plan_evidence` → `pac_delete_plan_evidence` |

## Não delegado (permanece na api-pac)

- Auth middleware GPT
- `pac_search_assignable_users` → core-api `GET /integrations/directory/users` (app `quality-action-plans`)
- `pac_search_similar_cases`, `pac_search_solution_patterns`, `pac_suggest_actions`
- Health, OpenAPI público
- Operações só do plugin: aprovar/rejeitar eficácia, dashboard, minha fila, audit log, etc.

## Implementação

```
quality_action_plans_router
  → pac_delpi_route_delegate (sempre)
  → PacApiDelpiDelegationService
  → ApiDelpiQualityGateway (httpx)
  → api-delpi /quality/action-plans/*
```

## Homologação

1. Subir delpi-central com `API_DELPI_INTERNAL_SERVICE_TOKEN` definido.
2. api-pac na rede `infra_delpi-network` com override srv-api.
3. `API_DELPI_BASE_URL` + token no `.env` da api-pac.
4. `GET /quality/action-plans/PAC-2026-XXXX` via api-pac retorna detalhe (código resolvido na api-delpi).
5. Criar plano via GPT (api-pac) e conferir registro no plugin (api-delpi).
6. `pytest tests/unit/test_pac_delpi_*_parity.py tests/unit/test_pac_api_delpi_delegation.py tests/unit/test_pac_plan_reference_routes.py`

## Referências

- Paridade: `tests/unit/test_pac_delpi_read_parity.py`, `test_pac_delpi_write_parity.py`
- Gateway: `app/infrastructure/gateways/api_delpi_quality_gateway.py`
- Middleware ator: `api-delpi/app/middleware/pac_service_actor_middleware.py`
