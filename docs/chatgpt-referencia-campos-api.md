# Referência PAC — campos, evidências e API (Conhecimento GPT)

Upload no builder (**Conhecimento**), junto com **`chatgpt-conhecimento-regras-gravacao.md`** (checklist de gravação + glossário) e os roteiros `.docx`. O system prompt compacto fica em `chatgpt-instrucoes-system-prompt.txt` (≤8.000 caracteres nas Instruções).

## Registro NC do cliente (`client_nc_registry`)

- NC **externa**: gravar o **número/registro da NC do cliente** (ex.: `217436500`).
- **Não** deixar esse número só em `source_reference` — `client_nc_registry` é o campo canônico para export 8D/PDF.
- `source_reference` complementa (ex.: título do PDF, e-mail).

## Datas (`detected_at`, `reported_at`)

- Formato **ISO 8601** apenas (ex.: `2026-06-24T10:00:00-03:00`)
- **Não** enviar texto livre (departamento, descrição, «produção do cliente», etc.) nesses campos — a API rejeita com erro de validação
- Se a data não for conhecida, **omitir** o campo

## Escopo NC (`nonconformity_scope`)

- Obrigatório no create: `internal` ou `external`
- `internal`: falha interna DELPI — priorize `department`
- `external`: reclamação cliente/fornecedor — priorize `customer_name` / `customer_contact`
- Não confundir com `source_type` (canal: email, pdf, manual_text, …)
- Sem integração TOTVS nesta fase; `source_reference` só se o analista informar

## Filial (`branch_code`)

- Obrigatório: `01` ou `02`
- Usar em buscas e recorrência

## Recorrência (`recurrence_key`)

- **Não** enviar chave inventada pelo agente.
- Omitir o campo no create — a API compõe: `filial:01|produto:…|falha:…`
- Detalhes e erros frequentes: `chatgpt-conhecimento-regras-gravacao.md` § 1 e § 5.

## Extração de relatos

Ver `extracao-estruturada-pdf-email.md` no repositório: rascunho `draft_extraction` + validação humana antes de gravar.

## Upload de evidências (`pac_attach_plan_evidence`)

Multipart obrigatório — não enviar JSON para arquivo.

| Campo | Obrigatório | Valores |
|-------|-------------|---------|
| `file` | Sim | PDF, imagem, planilha, etc. |
| `evidence_type` | Sim | email, message, spreadsheet, pdf, image, manual_text, system_reference, other |
| `section` | Não | general, nc_description, containment, root_cause, corrective, effectiveness, preventive, documentation, attachments |
| `description` | Não | Texto livre |
| `knowledge_visible` | Não (default true) | Histórico de inteligência |
| `action_id` | Não | UUID da ação vinculada |

Fluxo: `pac_create_plan_actions` → anexar com `action_id` se `evidence_required`. Listar/baixar/remover: `pac_list_plan_evidences`, `pac_download_plan_evidence`, `pac_delete_plan_evidence`. Tags: `pac_suggest_evidence_tags`, `pac_suggest_evidence_tags_from_image`.

## Eficácia

| Papel | Meio |
|-------|------|
| Analista submeter | `pac_submit_effectiveness_review` — effective, partially_effective, ineffective |
| Coordenação aprovar/rejeitar/fila | Plugin Minha DELPI (api-delpi) |
| Registro direto | `pac_record_effectiveness_review` — só se coordenação já validou offline |

## Status do plano

draft → triage → containment → root_cause_analysis → action_plan_defined → in_progress → waiting_validation → completed (ou cancelled)

Severidade: low, medium, high, critical

## Linguagem com o analista

- Na conversa: **não** expor `branch_code`, `nonconformity_scope`, snake_case, enums em inglês nem `operationId`.
- Glossário completo: **`chatgpt-conhecimento-regras-gravacao.md`** § 4.
- Nomes técnicos só nas chamadas à API.

## Actions disponíveis (25)

Inteligência: pac_search_similar_cases, pac_assess_recurrence_on_opening, pac_search_solution_patterns, pac_suggest_actions, pac_suggest_evidence_tags, pac_suggest_evidence_tags_from_image

Planos: pac_create/list/get/update_action_plan, pac_update_action_plan_status, pac_reopen_action_plan, pac_upsert_ishikawa, pac_upsert_five_whys, pac_create/update_plan_action, pac_upsert/export_rnc_8d, pac_list/attach/delete/download_plan_evidence, pac_submit/record_effectiveness_review

Coordenação/admin **não** estão na API PAC.
