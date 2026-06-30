# PAC — regras de gravação e glossário (Conhecimento GPT)

Anexe este arquivo em **Conhecimento** no builder do Custom GPT, junto com `chatgpt-referencia-campos-api.md` e os roteiros `.docx`. O **system prompt** (`chatgpt-instrucoes-system-prompt.txt`) fica compacto (limite 8.000 caracteres nas Instruções); **detalhes operacionais ficam aqui**.

---

## 1. Checklist antes de `pac_create_action_plan`

| Campo / regra | O que fazer |
|---------------|-------------|
| `branch_code` | Obrigatório: `01` ou `02`. Perguntar ao analista. |
| `nonconformity_scope` | Obrigatório: `internal` (falha interna) ou `external` (reclamação cliente/fornecedor). |
| `source_type` | Canal do relato: `email`, `pdf`, `message`, etc. — **não** é o escopo NC. |
| `client_nc_registry` | NC externa: número/registro **do cliente** (ex.: `217436500`). **Não** deixar só em `source_reference`. |
| `source_reference` | Referência livre do canal (ex.: «NC 217436500 - PDF WEG»). Complementa, não substitui `client_nc_registry`. |
| `customer_name` | Nome do cliente em NC externa. |
| `customer_code` / `customer_store` | Código e loja TOTVS/SA1 quando o analista informar ou confirmar. |
| `customer_contact` | Contato do cliente se disponível no relato. |
| `product_code` / `product_description` | Código e descrição do item reclamado. |
| `batch_number` | Lote, se informado. |
| `detected_at` / `reported_at` | Só **ISO 8601** (ex.: `2026-06-24T10:00:00-03:00`). Se desconhecida, **omitir** — nunca texto livre. |
| `problem_category` | Categoria **técnica** (ex.: «componente incorreto», «divergência de montagem»). **Não** usar «reclamação de cliente» (isso é escopo). |
| `failure_mode` | Modo de falha observável; pode ser texto ou lista separada por vírgula. |
| `symptom_tags` | Lista de sintomas/tags curtas. |
| `root_cause_category` | Só preencher quando o analista **confirmar** categoria (máquina, método, material, etc.). Na abertura, preferir omitir. |
| `recurrence_key` | **Não enviar** chave inventada (`WEG|produto|…`). Omitir o campo — a API monta: `filial:01|produto:10156007|falha:oxidação`. |
| `department` | Área interna que conduz ou onde ocorreu (conforme escopo); confirmar com analista. |
| `reported_problem` | Descrição factual do problema. |

---

## 2. Ordem de gravação após confirmação

1. `pac_create_action_plan` — identificação mínima completa (tabela acima).
2. `pac_upsert_ishikawa` — hipóteses por 6M; notas de pendência.
3. `pac_upsert_five_whys` — `occurrence_whys` e `detection_whys`; `root_cause` como hipótese; `confidence_level`: `low` | `medium` | `high`.
4. `pac_create_plan_actions` — contenção, corretivas, preventivas, verificação, padronização, treinamento; `responsible_name`, `department`, prazo, `cause_track` (`occurrence` | `detection`) quando couber.
   - **Opcional — Minha fila:** se o responsável for usuário DELPI, chamar `pac_search_assignable_users?q=nome` e gravar `responsible_user_id` (UUID retornado) **além** de `responsible_name`. Só nome livre → não entra na fila pessoal do plugin.
5. `pac_update_action_plan_status` — avançar status conforme estágio.
6. `pac_attach_plan_evidence` — **se** o analista enviou PDF, e-mail, foto ou planilha: anexar com `evidence_type` adequado (`pdf`, `email`, `image`, …).
7. `pac_upsert_rnc_8d` — só se template 8D do cliente for o fluxo acordado. Em `team_members[]`, opcional `member_user_id` (UUID via `pac_search_assignable_users`) além de `member_name` — habilita vínculo Delpi na equipe e herança de responsável nas ações.

---

## 3. Evidências (obrigatório quando há arquivo)

Se o analista colou texto **e** enviou arquivo, ou citou PDF da NC:

- Após criar o plano, usar `pac_attach_plan_evidence` (multipart: `file` + `evidence_type`).
- `evidence_type` comum: `pdf`, `email`, `image`, `spreadsheet`.
- `section` sugerida para NC inicial: `nc_description` ou `general`.
- Ações com `evidence_required: true` devem receber anexo quando o analista tiver o comprovante.

**Não** declarar `source_type: pdf` sem orientar o upload ou sem o analista confirmar que anexará depois no plugin.

---

## 4. Glossário — API → conversa com analista

Use **só português humanizado** em perguntas, resumos e confirmações.

| API (interno) | Falar com o analista |
|---------------|----------------------|
| `branch_code` | Filial 01 / Filial 02 |
| `nonconformity_scope` internal | NC interna (processo/produção DELPI) |
| `nonconformity_scope` external | Reclamação de cliente ou NC externa |
| `client_nc_registry` | Registro/número da NC do cliente |
| `customer_code` / `customer_store` | Código e loja do cliente no cadastro |
| `product_code` | Código do produto |
| `batch_number` | Lote |
| `detected_at` | Data da ocorrência |
| `reported_at` | Data do relato |
| `severity` low/medium/high/critical | Baixa / média / alta / crítica |
| `status` draft → … → completed | Rascunho → triagem → contenção → análise de causa → plano definido → em andamento → aguardando validação → concluído |
| `containment` | Contenção |
| `corrective` | Corretiva |
| `preventive` | Preventiva |
| `verification` | Verificação |
| `standardization` | Padronização |
| `training` | Treinamento |
| `cause_track` occurrence | Trilha de ocorrência (por que aconteceu) |
| `cause_track` detection | Trilha de detecção (por que não foi detectado antes) |
| `confidence_level` low/medium/high | Confiança baixa / média / alta na causa raiz |

---

## 5. Erros frequentes (evitar)

| Erro | Correção |
|------|----------|
| NC do cliente só em `source_reference` | Gravar número em `client_nc_registry` |
| `problem_category` = «reclamação de cliente» | Usar categoria técnica; escopo já está em `nonconformity_scope` |
| `recurrence_key` customizada | Omitir; deixar API compor |
| `root_cause_category` na abertura sem confirmação | Omitir até validação |
| Texto livre em `detected_at` | ISO 8601 ou omitir |
| Ishikawa/5P com causa fechada sem evidência | Marcar hipótese e confiança média/baixa |
| Plano gravado sem consultar histórico | Chamar `pac_search_similar_cases` antes de propor causa/ações |
| PDF citado sem anexo | Orientar `pac_attach_plan_evidence` ou registro manual no plugin |
| Expor `branch_code`, enums em inglês no chat | Traduzir sempre (§ 4) |
| Código PAC citado sem chamar a API | Usar `pac_get_action_plan` ou `?code=` — não inventar falha técnica |

---

## 6. Caso real — lições (PAC-2026-0029)

Registro via GPT com boa análise (Ishikawa, 5 Porquês, 9 ações), mas lacunas de cadastro:

- `client_nc_registry` vazio — número 217436500 ficou só em `source_reference`.
- `customer_code` / `customer_store` vazios — só nome WEG.
- Nenhuma evidência PDF anexada apesar de `source_type: pdf`.
- `recurrence_key` fora do padrão (`WEG|10156007|…`) — prejudica recorrência automática.
- `problem_category` = «reclamação de cliente» — confundiu escopo com categoria.

Use este caso como lembrete na próxima abertura de NC externa com PDF.

---

## 7. Referências de plano (`pac_get_action_plan` / `pac_list_action_plans`)

A **api-delpi** é fonte de verdade do CRUD; a API PAC repassa path e query inalterados (delegação S2S). A resolução de código → UUID ocorre na api-delpi.

### Formato aceito

| Formato | Exemplo | Quando usar |
|---------|---------|-------------|
| Código PAC | `PAC-2026-0029` | Analista citou o código na conversa — **preferir** |
| UUID | `f0e274de-cc4b-4b68-b9cb-881408f9374b` | Retornado no create/list; válido em qualquer `{plan_id}` |

Padrão: `PAC-` + ano (4 dígitos) + `-` + sequência (4 dígitos). A API normaliza maiúsculas/minúsculas no código.

### Fluxo recomendado

1. Analista menciona «PAC-2026-0029» → `pac_get_action_plan` com path `/quality/action-plans/PAC-2026-0029`.
2. Só o código, sem certeza → `pac_list_action_plans?code=PAC-2026-0029` (match exato) e depois o detalhe.
3. Escritas no mesmo plano (`pac_upsert_ishikawa`, ações, evidências, status, 8D…): reutilize o **mesmo código** ou o `id` retornado no detalhe.

Todas as rotas com `{plan_id}` no path aceitam código PAC ou UUID.

### Erros — como reagir

| Resposta | Significado | O que fazer |
|----------|-------------|-------------|
| **404** | Referência inválida ou plano inexistente | Confirmar código com o analista ou listar por cliente/produto |
| **503** `API_DELPI_MISCONFIGURED` | Infra (delegação não configurada) | Informar indisponibilidade temporária; não gravar |
| **422** | Path não é UUID nem código PAC válido | Corrigir para `PAC-YYYY-NNNN` ou UUID do plano |

**Não** responder ao analista com mensagem genérica do tipo «Tive falha ao abrir o detalhe pelo código» sem ter chamado a API ou sem explicar 404 de forma clara.

## 8. Documentação complementar (repositório)

- Campos e multipart: `chatgpt-referencia-campos-api.md`
- Setup do GPT: `chatgpt-especialista-qualidade.md`
- Extração de PDF/e-mail: `extracao-estruturada-pdf-email.md`
