# Referência PAC — campos, evidências e API (Conhecimento GPT)

Upload em **Conhecimento** (`docs/agente-gpt-import/conhecimento/`), junto com `chatgpt-conhecimento-regras-gravacao.md`, `extracao-estruturada-pdf-email.md`, `entrevista-ishikawa.md` e `entrevista-cinco-porques.md`. System prompt: `../instrucoes/chatgpt-instrucoes-system-prompt.txt` (colar em **Instruções**).

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
- `external`: reclamação cliente/fornecedor — priorize `customer_name` e **papéis de contato separados** (ver § Contatos cliente vs DELPI abaixo)
- Não confundir com `source_type` (canal: email, pdf, manual_text, …)
- Sem integração TOTVS nesta fase; `source_reference` só se o analista informar

## Filial (`branch_code`)

- Obrigatório: `01` ou `02`
- Usar em buscas e recorrência

## Responsável da ação (`responsible_name` / `responsible_user_id`)

| Campo | Quando usar |
|-------|-------------|
| `responsible_name` | Sempre que houver responsável (texto livre ou nome do usuário Delpi). |
| `responsible_user_id` | Opcional. UUID de usuário Delpi com acesso ao app PAC — obtido via `pac_search_assignable_users?q=…` (mín. 2 caracteres). |
| Só nome, sem UUID | Válido; a ação **não** aparece na Minha fila do plugin. |
| Nome + UUID | A ação entra na **Minha fila** do usuário vinculado. |

`pac_update_plan_action` também aceita `responsible_user_id` (ou `null` para desvincular).

## Contatos cliente vs interlocutores DELPI (V025 — jun/2026)

**Não misturar papéis.** O campo legado `customer_contact` significa **pessoa de contato no cliente** (destinatário formal do 8D — «Atenção para» na planilha WEG). O vendedor ou comercial DELPI vai em campos próprios.

| Campo API | Papel | Planilha 8D WEG (referência) |
|-----------|--------|------------------------------|
| `customer_contact` | Contato **no cliente** (ex.: Igor) | G21 — Atenção para |
| `customer_contact_email` | E-mail do contato no cliente | J21 |
| `customer_contact_phone` | Telefone do contato no cliente | — |
| `delpi_contact_name` | Interlocutor DELPI no caso (ex.: Laercio) | J5 — Contato |
| `delpi_contact_area` | Área DELPI: `comercial`, `qualidade`, `pcp`, `engenharia`, `outro` | PDF/UI |
| `delpi_sales_rep` | Vendedor DELPI (se distinto do interlocutor) | PDF/UI |
| `delpi_quality_contact` | Referência qualidade DELPI (ex.: Carla) | PDF/UI |
| `template_payload.contact_phone` | Telefone **DELPI** (comercial) | J6 |

No detalhe do plano, a API expõe também `contact_roles` (visão já resolvida para leitura/export).

### Regras para o agente

1. **E-mail/PDF WEG:** remetente ou «Atenção para» / assinatura do cliente → `customer_contact` + `customer_contact_email`; comercial/vendedor DELPI citado no corpo → `delpi_contact_name` (e `delpi_sales_rep` se for só o vendedor).
2. **Não** gravar o vendedor DELPI em `customer_contact` quando o contato do cliente for outra pessoa.
3. Em `pac_upsert_rnc_8d`, enviar os campos de contato no corpo do PUT (não só em `template_payload.attention_to` — a API sincroniza legado, mas a fonte canônica são as colunas do plano).
4. Dados antigos invertidos (vendedor em `customer_contact`, cliente em `template_payload.attention_to`): a API e o export corrigem na leitura; ao regravar, separar nos campos certos.

## Equipe de análise 8D (`team_members` em `pac_upsert_rnc_8d`)

| Campo | Quando usar |
|-------|-------------|
| `member_name` | Obrigatório por membro (texto). |
| `member_user_id` | Opcional. UUID Delpi via `pac_search_assignable_users?q=…` — habilita Minha fila e notificações para o membro. |
| `is_leader` | Líder da equipe (bool). |
| `department` | Área/função (texto). |
| `sort_order` | Ordem de exibição (int). |

No plugin MFE, ações novas podem **herdar** `responsible_user_id` do membro vinculado. Planos internos (sem 8D) ainda permitem vínculo Delpi direto no modal da ação.

## 5 Porquês e causa raiz (`pac_upsert_five_whys`)

| Campo | Uso |
|-------|-----|
| `occurrence_whys` | Lista ordenada — por que o defeito aconteceu |
| `detection_whys` | Lista ordenada — por que não foi detectado antes |
| `root_cause` | Texto da **causa raiz provável** (hipótese até confirmação) |
| `confidence_level` | `low` \| `medium` \| `high` — alinhar à faixa % da conversa (ver `chatgpt-conhecimento-regras-gravacao.md` §5) |

Na conversa com o analista, **sempre** exibir também **Nível de confiança: XX%** e lacunas se &lt; 70%.

## Ações do plano (`pac_create_plan_actions`)

| Campo | Uso |
|-------|-----|
| `action_type` | `containment`, `corrective`, `preventive`, `verification`, `standardization`, `training` |
| `cause_track` | `occurrence` ou `detection` — **obrigatório em toda corretiva** vinculada a um bloco dos Porquês |

### Corretivas mínimas por trilha dos Porquês

Regra obrigatória ao **propor** e **gravar** o plano (detalhes em `chatgpt-conhecimento-regras-gravacao.md` §5):

| Se existir em `pac_upsert_five_whys` | Então no plano |
|--------------------------------------|----------------|
| ≥1 resposta em `occurrence_whys` | ≥1 ação `corrective` com `cause_track: occurrence` |
| ≥1 resposta em `detection_whys` | ≥1 ação `corrective` com `cause_track: detection` |

Contenção e preventivas **não** contam para essa cobertura. Cada corretiva deve atacar a causa raiz ou o porquê consolidado da respectiva trilha.

## Código do plano (`code`)

Persistência e resolução na **api-delpi**; a API PAC delega path/query sem alterar.

| Operação | Referência no path / query |
|----------|----------------------------|
| `pac_get_action_plan` | Path: **UUID** ou código **`PAC-2026-XXXX`** |
| `pac_list_action_plans` | Query opcional `code` (match exato, normalizado para maiúsculas) |
| Demais rotas `{plan_id}` (Ishikawa, ações, evidências, status, 8D, eficácia…) | Mesmo: código PAC ou UUID |

**Fluxo:** quando o analista citar `PAC-2026-0029`, chame o detalhe com esse código; use o mesmo código ou o `id` retornado nas escritas seguintes. Se 404, confirme o código — não assuma erro técnico opaco.

O detalhe inclui `contact_roles` (nomes/e-mails já resolvidos para cliente vs DELPI) — use para validar antes de export 8D.

Padrão do código: `^PAC-\d{4}-\d{4}$` (ex.: `PAC-2026-0029`).

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

Fluxo: `pac_create_plan_actions` → anexar com `action_id` se `evidence_required`. Listar/baixar/remover: `pac_list_plan_evidences`, `pac_download_plan_evidence`, `pac_delete_plan_evidence`. **Editar metadados** (tipo, seção 8D, vínculo à ação, descrição): `pac_update_plan_evidence`. **Ler conteúdo textual** (planilha/PDF quando suportado): `pac_get_plan_evidence_content` — preferir para o GPT analisar `.xlsx` sem depender só do download binário. Tags: `pac_suggest_evidence_tags`, `pac_suggest_evidence_tags_from_image`.

## Exportação Excel 8D (`pac_list_export_templates`, `pac_export_rnc_8d`)

| Campo / parâmetro | Uso |
|-------------------|-----|
| `pac_list_export_templates` | Catálogo de modelos: `weg_wfr20997` (WEG WFR-20997) e `delpi_8d` (DELPI). |
| `export_template_key` | Preferência no plano (`pac_create_action_plan` / `pac_update_action_plan`). Chaves válidas do catálogo. |
| `template_key` (query) | Em `pac_export_rnc_8d`: escolhe o modelo na exportação. Omitir = usar `export_template_key` do plano, hint do cliente (ex.: WEG) ou padrão WEG. |

Fluxo recomendado: listar catálogo → gravar `export_template_key` no plano quando o analista confirmar o cliente → `pac_export_rnc_8d?template_key=…` se precisar trocar só na exportação.

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

## Actions disponíveis (30)

Inteligência: pac_search_similar_cases, pac_assess_recurrence_on_opening, pac_search_solution_patterns, pac_suggest_actions, pac_suggest_evidence_tags, pac_suggest_evidence_tags_from_image

Planos: pac_create/list/get/update_action_plan, pac_update_action_plan_status, pac_reopen_action_plan, pac_upsert_ishikawa, pac_upsert_five_whys, pac_create/update_plan_action, pac_upsert_rnc_8d, **pac_list_export_templates**, **pac_export_rnc_8d** (`template_key` opcional), pac_list/attach/update/delete/download_plan_evidence, **pac_get_plan_evidence_content**, pac_submit/record_effectiveness_review, **pac_search_assignable_users**

Coordenação/admin **não** estão na API PAC.
