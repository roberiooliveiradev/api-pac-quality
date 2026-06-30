# PAC — regras de gravação e glossário (Conhecimento GPT)

Pasta de importação: `docs/agente-gpt-import/conhecimento/`. Anexe este arquivo em **Conhecimento** no builder, junto com `chatgpt-referencia-campos-api.md`, `extracao-estruturada-pdf-email.md`, `entrevista-ishikawa.md` e `entrevista-cinco-porques.md`. O **system prompt** fica em `../instrucoes/chatgpt-instrucoes-system-prompt.txt` (colar em **Instruções**, ≤8.000 caracteres).

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
   - **Cobertura obrigatória (corretivas × 5 Porquês):** se um bloco dos Porquês tiver **pelo menos um nível** respondido, o plano proposto deve ter **no mínimo 1 ação corretiva** (`action_type: corrective`) com `cause_track` da mesma trilha:
     - `occurrence_whys` com resposta → ≥1 corretiva com `cause_track: occurrence` (por que aconteceu).
     - `detection_whys` com resposta → ≥1 corretiva com `cause_track: detection` (por que não foi detectado antes).
     - Se **ambos** os blocos existirem, **ambos** precisam de ao menos uma corretiva vinculada — não basta ações só na trilha de ocorrência.
     - Contenção, preventivas, verificação e padronização **não substituem** essa corretiva mínima por trilha.
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
| `export_template_key` | Modelo Excel 8D preferido (`weg_wfr20997`, `delpi_8d`) — ver catálogo `pac_list_export_templates` |
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
| `confidence_level` low/medium/high | Confiança na causa raiz — exibir também como **%** na conversa (ver §5) |

---

## 5. Causa raiz provável e nível de confiança (requisito prioritário — liderança jun/2026)

Após Ishikawa e 5 Porquês, **sempre** apresentar ao analista — antes de propor o plano definitivo:

### Bloco obrigatório na conversa

```markdown
### Causa raiz provável
[Uma frase objetiva. Se ainda hipótese: «Hipótese principal: …»]

### Nível de confiança
**XX%** — [justificativa em 1–2 frases: histórico, evidências, profundidade dos Porquês]

### O que falta levantar
[Somente se confiança < 70% — lista numerada de lacunas]
```

### Faixas percentuais (conversa ↔ API)

| Confiança na conversa | `confidence_level` em `pac_upsert_five_whys` | Quando usar |
|----------------------|-----------------------------------------------|-------------|
| 30% – 55% | `low` | Poucas evidências; hipóteses Ishikawa não validadas; sem casos similares alinhados |
| 56% – 79% | `medium` | Alguma evidência ou histórico parcial; analista confirmou parte da cadeia de Porquês |
| 80% – 95% | `high` | Evidências consistentes, histórico alinhado, analista validou causa; **nunca 100%** sem confirmação explícita |

### Como estimar o percentual (orientação)

Some mentalmente fatores — não é fórmula rígida, mas deve ser **explicável**:

| Fator | Aumenta confiança | Reduz confiança |
|-------|-------------------|-----------------|
| Casos similares na DELPI com mesma causa | +15 a +25% | Nenhum histórico consultado |
| Evidência física (foto, PDF, amostra descrita) | +10 a +20% | Só relato verbal vago |
| Ishikawa com hipótese testada/descartada | +10% | Só lista de suspeitas |
| Cadeia de 5 Porquês até causa sistêmica | +15% | Parou no sintoma |
| Analista confirmou a causa | +20% | Causa inferida sem validação |
| Recorrência conhecida (`pac_assess_recurrence_on_opening`) | +10% | Primeira ocorrência sem padrão |

### Se confiança &lt; 70%

Liste **objetivamente** o que o analista deve levantar, por exemplo:

- Confirmar lote, data e linha de produção
- Solicitar amostra física ou foto do defeito
- Verificar registro de processo / ordem de produção
- Entrevistar operador ou inspetor da etapa
- Conferir especificação do cliente vs. desenho interno
- Anexar PDF da NC do cliente (`pac_attach_plan_evidence`)

**Não** proponer encerramento da investigação como se a causa estivesse fechada.

### Gravação na API

- `pac_upsert_five_whys`: `root_cause` = texto da causa provável; `confidence_level` = faixa da tabela.
- `root_cause_category` no plano: só após analista confirmar categoria 6M (máquina, método, material…).
- Se confiança `low`, registre em notas do Ishikawa as pendências de investigação.

### Ações corretivas por trilha dos Porquês (obrigatório no plano proposto)

Antes de pedir confirmação para gravar, valide a **cobertura mínima**:

| Bloco em `pac_upsert_five_whys` | Condição | Mínimo no plano (`pac_create_plan_actions`) |
|--------------------------------|----------|---------------------------------------------|
| `occurrence_whys` | ≥1 nível com resposta substantiva | ≥1 ação `corrective` com `cause_track: occurrence` |
| `detection_whys` | ≥1 nível com resposta substantiva | ≥1 ação `corrective` com `cause_track: detection` |

Na conversa, apresente as corretivas **agrupadas por trilha** (ocorrência / detecção) e deixe explícito qual porquê ou causa raiz cada ação endereça. Se faltar corretiva em alguma trilha preenchida, **não** proponha o plano como completo — complete ou explique a lacuna ao analista.

### Banco de conhecimento

Cada PAC alimenta futuras análises: casos semelhantes, padrões de solução, ações eficazes, recorrências, rejeições de eficácia. Ao citar histórico, informe **código PAC**, resultado de eficácia e o que foi reutilizado na sugestão atual.

---

## 6. Erros frequentes (evitar)

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
| Análise sem causa raiz provável ou sem % de confiança | Incluir bloco obrigatório §5 antes do plano de ação |
| Confiança alta sem evidência ou confirmação | Reduzir % e listar lacunas em «O que falta levantar» |
| Porquês de ocorrência e/ou detecção preenchidos sem corretiva na mesma trilha | Incluir ≥1 `corrective` com `cause_track: occurrence` e/ou `detection` conforme §5 — ver tabela «Ações corretivas por trilha» |

---

## 7. Caso real — lições (PAC-2026-0029)

Registro via GPT com boa análise (Ishikawa, 5 Porquês, 9 ações), mas lacunas de cadastro:

- `client_nc_registry` vazio — número 217436500 ficou só em `source_reference`.
- `customer_code` / `customer_store` vazios — só nome WEG.
- Nenhuma evidência PDF anexada apesar de `source_type: pdf`.
- `recurrence_key` fora do padrão (`WEG|10156007|…`) — prejudica recorrência automática.
- `problem_category` = «reclamação de cliente» — confundiu escopo com categoria.

Use este caso como lembrete na próxima abertura de NC externa com PDF.

---

## 8. Referências de plano (`pac_get_action_plan` / `pac_list_action_plans`)

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

## 9. Documentação complementar (repositório)

- Campos e multipart: `chatgpt-referencia-campos-api.md` (mesma pasta)
- Extração PDF/e-mail: `extracao-estruturada-pdf-email.md` (mesma pasta)
- Setup do GPT (humano): `../../chatgpt-especialista-qualidade.md`
