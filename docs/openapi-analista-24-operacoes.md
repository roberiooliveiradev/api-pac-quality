# OpenAPI api-pac-quality — 24 operações (fluxo analista GPT)

## Contexto

O **ChatGPT Custom GPT** aceita no máximo **30 operações** por action set. A API PAC chegou a expor **31 rotas `pac_*` + `/health`** (~32 no schema), bloqueando a importação do OpenAPI no builder («Especialista Qualidade»).

## Decisão (jun/2026)

Em vez de manter um schema filtrado (`/openapi.chatgpt.json`) com allowlist JSON editável:

1. A **`api-pac-quality`** publica **somente** o fluxo do **analista** em `GET /openapi.json` — **24 operações**.
2. Funcionalidades de **coordenação, auditoria, cron e grafo avançado** ficam **apenas no plugin Minha DELPI** (`api-delpi`), com RBAC por usuário — mais seguro para o agente GPT com chave compartilhada.
3. `GET /health` permanece na API mas **fora do OpenAPI** (`include_in_schema=False`) para não consumir cota do ChatGPT.

## Operações expostas ao GPT (24)

| Grupo | operationId |
|-------|-------------|
| Inteligência | `pac_search_similar_cases`, `pac_assess_recurrence_on_opening`, `pac_search_solution_patterns`, `pac_suggest_actions`, `pac_suggest_evidence_tags`, `pac_suggest_evidence_tags_from_image` |
| Planos — leitura | `pac_list_action_plans`, `pac_get_action_plan`, `pac_list_plan_evidences`, `pac_download_plan_evidence`, `pac_export_rnc_8d` |
| Planos — escrita | `pac_create_action_plan`, `pac_update_action_plan`, `pac_update_action_plan_status`, `pac_reopen_action_plan` |
| Análise | `pac_upsert_ishikawa`, `pac_upsert_five_whys` |
| Ações | `pac_create_plan_actions`, `pac_update_plan_action` |
| 8D | `pac_upsert_rnc_8d` |
| Evidências | `pac_attach_plan_evidence`, `pac_delete_plan_evidence` |
| Eficácia (analista) | `pac_submit_effectiveness_review`, `pac_record_effectiveness_review` |

Fonte única no código: `app/interface/http/route_contract_registry.py` → `ANALYST_PAC_OPERATION_IDS`.

## Somente plugin (api-delpi) — removidas da api-pac

| operationId | Motivo |
|-------------|--------|
| `pac_dispatch_notifications` | Cron/batch administrativo |
| `pac_list_pending_effectiveness_reviews` | Fila de coordenação |
| `pac_approve_effectiveness_review` | Aprovação — perfil coordenador |
| `pac_reject_effectiveness_review` | Rejeição — perfil coordenador |
| `pac_list_plan_audit_log` | Trilha de auditoria |
| `pac_promote_solution_pattern` | Promoção a padrão pós-fechamento |
| `pac_get_quality_knowledge_graph` | Grafo avançado — não essencial no fluxo 8D conversacional |

## Configuração do Custom GPT

1. **Actions** → Importar de URL: `https://pac-api.minhadelpi.com.br/openapi.json`
2. Autenticação: **Chave API** → Bearer (`PAC_QUALITY_API_KEY`)
3. Reimportar o schema após cada deploy que altere rotas.

Guias: [chatgpt-especialista-qualidade.md](chatgpt-especialista-qualidade.md) · [chatgpt-acoes-api-key.md](chatgpt-acoes-api-key.md)

## Gates e homologação

| Onde | Comando |
|------|---------|
| CI local api-pac | `python scripts/audit_pac_openapi_operation_limit.py --check` |
| CI smoke | `scripts/ci-smoke.sh` (inclui gate + `test_pac_openapi_operation_limit.py`) |
| Produção (delpi-central) | `scripts/homologacao/check-pac-api-server.sh` |

O gate falha se:

- houver mais de **30** operações no OpenAPI;
- o conjunto publicado ≠ **24** `ANALYST_PAC_OPERATION_IDS`;
- `/health` aparecer no schema;
- operações plugin-only voltarem ao OpenAPI PAC.

## Testes de paridade

- `tests/unit/test_pac_delpi_read_parity.py` — leituras GPT vs `PLUGIN_ONLY_READ_PARITY`
- `tests/unit/test_pac_delpi_write_parity.py` — escritas GPT vs `PLUGIN_ONLY_WRITE_PARITY`
- Evals EVAL13/EVAL15/EVAL16 — cenários de coordenação orientam uso do plugin, não da API PAC

## Deploy

```bash
cd ~/projetos/api-pac-quality
git pull
docker compose up -d --build --force-recreate api-pac-quality
```

Validar:

```bash
curl -s https://pac-api.minhadelpi.com.br/openapi.json | python3 -c "
import json,sys; ops=[o.get('operationId') for p in json.load(sys.stdin).get('paths',{}).values() for o in p.values() if isinstance(o,dict)]; print(len(ops), 'operações')"
# Esperado: 24 operações
```
