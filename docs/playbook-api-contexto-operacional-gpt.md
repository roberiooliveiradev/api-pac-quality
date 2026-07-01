# Playbook — API de contexto operacional para o Especialista Qualidade (GPT)

**Status:** P2 implementado (jun/2026) — repo `api-pac-context` com **28 rotas** `ctx_*` (allowlist §8)  
**Público:** api-pac-quality, api-delpi, produto PAC, arquitetura DELPI  
**Relacionados:** [playbook_pac_qualidade_delpi.md](../playbook_pac_qualidade_delpi.md) · [openapi-analista-24-operacoes.md](openapi-analista-24-operacoes.md) · [contrato-http-api-pac-api-delpi.md](contrato-http-api-pac-api-delpi.md) · api-delpi `docs/api/11-guia-agente-chat.md` · Playbook 15 (rotas operacionais)

---

## 1. Contexto

A **api-delpi** já expõe dezenas de rotas REST com dados do Protheus/TOTVS úteis na investigação de qualidade:

- cadastro e contexto de **produto** (BOM, roteiro, inspeção QP, desenho);
- **PCP** e produção (programação, OPs, apontamentos, consumo, refugo);
- **qualidade** (NC cadastradas no TOTVS, PPM, inspeções de entrada);
- **PAC** (planos de ação — já consumidos pela api-pac-quality).

O **Especialista Qualidade** (Custom GPT) hoje usa a **api-pac-quality** com **26 operações** `pac_*` (limite ChatGPT: **30 por action set**). Essa API cobre registro PAC, inteligência histórica e fluxo 8D — **não** expõe o universo operacional da api-delpi.

O analista, durante Ishikawa e 5 Porquês, precisa cruzar o relato com fatos do ERP: estrutura do PA, roteiro, OP do lote, apontamentos, NC anteriores no TOTVS, inspeção de recebimento da MP, etc. Hoje isso depende de memória humana ou de outro canal (plugin Minha DELPI, chat interno).

---

## 2. Problema

| Sintoma | Causa |
|---------|--------|
| GPT propõe causa/ação sem consultar OP, BOM ou apontamento | Action set PAC não inclui rotas operacionais |
| Não há espaço para «colar» dezenas de rotas api-delpi no mesmo GPT | 26/30 slots já ocupados por `pac_*` |
| Agente externo não usa JWT/RBAC do plugin | api-delpi não é superfície direta para GPT |
| SQL ad hoc (`POST /data/sql`) é arriscado em agente de qualidade | Playbook 15 migrou para REST; GPT deve preferir rotas declarativas |

**Regra-mãe:** criar uma **API irmã** (BFF fino, como api-pac-quality) que **delegue leitura** à api-delpi com auth de serviço, OpenAPI curado e `operationId` estáveis para o agente — **sem** duplicar regra de negócio nem persistência.

---

## 3. Objetivo

| Item | Proposta |
|------|----------|
| Nome produto | **PAC Context API** / **API Contexto Operacional PAC** |
| Nome técnico repo | `api-pac-context` (ou `api-quality-context`) |
| Prefixo OpenAPI | `ctx_*` (ex.: `ctx_get_product_structure` → api-delpi `get_product_structure`) |
| Domínio | **Somente leitura** investigativa (GET + POST idempotente de busca se necessário) |
| Consumidor primário | Custom GPT **Especialista Qualidade** (e futuros agentes de qualidade) |
| Fonte de verdade | **api-delpi** (contrato `meta`, `entity`, `shape`) |

**Fora de escopo desta API:**

- CRUD PAC (permanece em api-pac-quality);
- coordenação, aprovação de eficácia, audit log administrativo;
- escrita em Protheus;
- substituir o pipeline do **Minha DELPI Chat** (`operational_route_registry`, `operationalFocus`).

---

## 4. Restrição ChatGPT — 30 operações

### 4.1 Situação atual

```
Especialista Qualidade (1 Custom GPT)
└── Action set api-pac-quality: 26 operações pac_*
    └── Margem: 4 slots (insuficiente para contexto operacional)
```

### 4.2 Estratégias possíveis

| ID | Estratégia | Prós | Contras |
|----|------------|------|---------|
| **S1** | **Segundo Custom GPT** («Investigador Operacional DELPI») com action set só `ctx_*` | Mantém PAC intacto; curadoria clara; até 30 rotas de contexto | Usuário alterna entre GPTs ou copia contexto manualmente |
| **S2** | **Dois action sets no mesmo GPT** | Um único assistente na UI | ChatGPT aceita **um** schema OpenAPI por GPT — exige **gateway unificado** ou MCP |
| **S3** | **Fachada agregada** (`ctx_investigate_product`, `ctx_investigate_production_order`) | Poucas operações; uma chamada = vários dados | Implementação e manutenção na BFF; perde granularidade |
| **S4** | **Reduzir** `pac_*` e misturar PAC + contexto em 30 ops | Um único endpoint OpenAPI | Regressão no fluxo analista; alta complexidade de allowlist |

**Recomendação inicial:** **S1 + S3 em fases**

1. **Fase 0–1:** segundo repo `api-pac-context` com rotas **1:1** curadas (≤30 GETs) — GPT investigador ou segunda Action no mesmo workspace se a plataforma evoluir.
2. **Fase 2:** endpoints **compostos** na BFF para reduzir chamadas em turnos longos (bundle produto + OP).

Documentar no builder: o analista pode usar **Especialista Qualidade** (PAC) e, na mesma conversa, invocar @GPT investigador **ou** colar resumo — até existir orquestração única.

---

## 5. Arquitetura proposta

```
┌─────────────────────────┐
│ Custom GPT Qualidade    │
│ (26 ops pac_*)          │
└───────────┬─────────────┘
            │ PAC_QUALITY_API_KEY
            ▼
┌─────────────────────────┐     S2S      ┌──────────────────┐
│ api-pac-quality         │─────────────►│ api-delpi        │
│ CRUD PAC + inteligência │              │ /quality/action- │
└─────────────────────────┘              │  plans/*         │
                                         └────────▲─────────┘
┌─────────────────────────┐                       │
│ Custom GPT Contexto     │                       │ delegação
│ (≤30 ops ctx_*)         │                       │
└───────────┬─────────────┘                       │
            │ PAC_CONTEXT_API_KEY                   │
            ▼                                       │
┌─────────────────────────┐───────────────────────┘
│ api-pac-context (novo)  │
│ BFF leitura investigativa│
│ OpenAPI allowlist       │
└─────────────────────────┘
```

**Espelhar padrão api-pac-quality:**

| Peça | Referência PAC |
|------|----------------|
| Auth entrada | `PAC_CONTEXT_API_KEY` (Bearer / `X-Api-Key`) |
| S2S api-delpi | `X-Delpi-Service-Token`, `X-Delpi-Caller-App: api-pac-context`, `X-Delpi-Actor-Id` |
| Delegação | Gateway httpx + repasse path/query; sem persistência local |
| OpenAPI | Allowlist `ANALYST_CONTEXT_OPERATION_IDS` + gate ≤30 |
| Mapeamento IDs | `ctx_*` ↔ `get_*` / `list_*` api-delpi |
| Extensões | `x-delpi` via injector + `route_contract_registry` espelho |
| Health | Fora do schema OpenAPI |

**Permissões api-delpi (S2S):** serviço com escopo leitura operacional (`api-delpi.access`, `api-delpi.quality.access`, leitura PAC se necessário para cruzamento).

---

## 6. Princípios de curadoria

1. **Leitura antes de SQL** — preferir rota REST com `operationId` e presenter; `execute_readonly_sql` só como último recurso (Tier C).
2. **Uma intenção investigativa → uma rota primária** — tabela §9.
3. **Produto + OP + lote** — parâmetros que o GPT já coleta no fluxo PAC (`product_code`, `batch_number`, filial `01`/`02`).
4. **Não duplicar inteligência PAC** — `similar-cases`, `recurrence`, `suggest_actions` permanecem em api-pac-quality.
5. **Composites na BFF** — quando 3+ rotas forem sempre usadas juntas na mesma pergunta.
6. **Apresentação** — respostas api-delpi já trazem `meta.entity`; BFF não reformatar markdown (agente consome JSON + resume em PT).

---

## 7. Inventário api-delpi por domínio

Legenda:

| Tier | Significado |
|------|-------------|
| **A** | Candidata forte à allowlist `ctx_*` (investigação PAC) |
| **B** | Útil sob demanda; plugin ou fase 2 |
| **C** | Fora do GPT contexto (admin, KPI agregado, escrita, SQL cru) |

### 7.1 Produto — cadastro, BOM, roteiro, contexto fabril

Prefixo: `/products`

| Tier | Path | operation_id (api-delpi) | Uso na investigação PAC |
|------|------|--------------------------|-------------------------|
| A | `GET /products/search` | `search_products` | Resolver código/descrição citados no relato |
| A | `GET /products/{code}` | `get_product_detail` | Cadastro leve do item reclamado |
| A | `GET /products/{code}/summary` | `get_product_summary` | Cadastro + estoque amostra |
| A | `GET /products/{code}/structure` | `get_product_structure` | **BOM** — componentes, revisão estrutura |
| A | `GET /products/{code}/structure/exclusivity` | `get_product_structure_exclusivity` | MP exclusiva / alternativas |
| A | `GET /products/{code}/guide` | `get_product_guide` | **Roteiro** (CTs, operações SG2) |
| A | `GET /products/{code}/inspection` | `get_product_inspection` | Ensaios **QP** do produto (≠ expedição) |
| A | `GET /products/{code}/production-status` | `get_product_production_status` | PA/PI, **OPs e apontamentos** até data ref. |
| A | `GET /products/{code}/factory-status` | `get_product_factory_status` | Visão integrada (estrutura + OP + expedição) |
| A | `GET /products/{code}/shipping-status` | `get_product_shipping_status` | PA pós-inspeção final |
| A | `GET /products/{code}/stock` | `get_product_stock` | Saldo MP/PA por filial |
| A | `GET /products/{code}/internal-movements` | `get_product_internal_movements` | Movimentos internos (filtro OP) |
| A | `GET /products/{code}/parents` | `get_product_parents` | Onde o item é usado (BOM reversa) |
| A | `GET /products/{code}/drawing` | `get_product_drawing` | Metadados desenho técnico |
| B | `GET /products/{code}/analyser` | `get_product_analyser` | Ficha multi-dimensão (substitui várias chamadas — candidato **composite** fase 2) |
| B | `GET /products/{code}/suppliers` | `get_product_suppliers` | Rastreio fornecedor MP |
| B | `GET /products/{code}/last-purchase` | `get_product_last_purchase` | Última compra MP |
| B | `GET /products/{code}/directives/{id}` | `get_product_directives` | Diretiva cliente → BOM |
| B | `GET /products/drawings` | `list_product_drawings` | Catálogo desenhos |
| C | `GET /products/{code}/pricing`, `/sales/*` | vários | Comercial — contexto secundário |
| C | `GET /products/{code}/cost-impact-simulation` | `get_product_cost_impact_simulation` | Simulador custo — fora do fluxo NC típico |

**Distinções críticas para o agente:**

| Rota | Não confundir com |
|------|-------------------|
| `/inspection` | Inspeção **QP** cadastrada no produto |
| `/shipping-status` | Quantidade após inspeção **final** PA |
| `/guide` | Roteiro de processo (não é PCP do dia) |
| `/production-status` | OPs/apontamentos do PA (melhor ponto de partida com lote/OP) |

---

### 7.2 PCP e produção — OPs, programação, apontamentos, consumo, perdas

Prefixo: `/production` (+ `/purchases` onde indicado)

| Tier | Path | operation_id | Uso na investigação PAC |
|------|------|--------------|-------------------------|
| A | `GET /production/orders/by-op/{production_order}` | `get_production_order_by_op` | **Detalhe da OP** citada no relato |
| A | `GET /production/oee/appointments/{appointment_id}` | `get_production_oee_appointment_by_id` | **Apontamento** com roteiro, BOM, tempos, achados |
| A | `GET /production/oee` | `get_production_oee` | Listar apontamentos (filtro OP/produto/data) |
| A | `GET /production/schedule/today` | `get_production_schedule_today` | Programação PCP do dia |
| A | `GET /production/orders/open` | `get_production_orders_open` | OPs abertas na data |
| A | `GET /production/orders/finished` | `get_production_orders_finished` | OPs finalizadas (janela) |
| A | `GET /production/planned-vs-real-time` | `get_production_planned_vs_real_time` | Planejado × real — desvio de processo |
| A | `GET /production/losses/records` | `get_production_losses_records` | Detalhe **refugo/scrap** |
| A | `GET /production/losses/top-materials` | `get_production_losses_top_materials` | Ranking perdas MP |
| A | `GET /production/consumption/by-item/{code}` | `get_production_consumption_by_item` | Consumo de MP no PA pai |
| B | `GET /production/consumption/top-items` | `get_production_consumption_top_items` | Ranking consumo período |
| B | `GET /production/consumption/top-items-validated` | `get_production_consumption_top_items_validated` | Consumo com apontamento confirmado |
| B | `GET /production/allocation-gaps` | `get_production_allocation_gaps` | Componente sem empenho |
| B | `GET /production/orders/finished-without-consumption` | `get_production_orders_finished_without_consumption` | OP finalizada sem baixa MP |
| B | `GET /production/work-centers/order-summary` | `get_production_work_center_order_summary` | OPs por centro de trabalho |
| B | `GET /production/eficiencia-fabril/appointments` | `list_eficiencia_fabril_appointments` | Bulk apontamentos |
| C | `GET /production/oee/series`, `/otd/series` | vários | Séries dashboard |
| C | `GET /production/direct_labor_cost_pct` | vários | KPI financeiro estratégico |

---

### 7.3 Qualidade — NC TOTVS, PPM, inspeções de entrada

| Tier | Path | operation_id | Uso na investigação PAC |
|------|------|--------------|-------------------------|
| A | `GET /quality/nonconformities` | `list_nonconformities` | **NC já registradas no Protheus** (produto, período, tipo) |
| A | `GET /quality/produced-quantity` | `get_produced_quantity` | Qtd produzida (CT inspeção final) |
| A | `GET /inspecoes-entrada/historico` | `get_inspecoes_entrada_historico` | Histórico inspeção **recebimento** MP |
| A | `GET /inspecoes-entrada/historico/detalhe` | `get_inspecoes_entrada_historico_detalhe` | Detalhe laudo + ensaios QER |
| A | `GET /inspecoes-entrada/rejeitadas-produto` | `get_inspecoes_entrada_rejeitadas_produto` | Rejeições por produto |
| B | `GET /quality/nonconformities/series` | `get_nonconformity_series` | Série temporal NC |
| B | `GET /quality/ppm/internal` | `list_ppm_internal` | PPM interno detalhado |
| B | `GET /quality/ppm/external` | `list_ppm_external` | PPM externo detalhado |
| B | `GET /inspecoes-entrada/pendentes` | `get_inspecoes_entrada_pendentes` | Laudos pendentes |
| B | `GET /quality/branches` | `list_quality_branches` | Filiais para filtro |
| C | `GET /quality/audit-5s/*` | `audit_5s_*` | Módulo 5S — paralelo ao PAC |
| C | `GET /quality/kaizens/*` | `kaizen_*` | Kaizen — melhoria contínua |

**PAC (planos de ação):** leitura transacional já disponível via `pac_get_action_plan` / `pac_list_action_plans` na api-pac-quality. **Não** reexpor na api-pac-context salvo leitura cruzada TOTVS↔PAC em fase 2 (`ctx_correlate_totvs_nc_with_pac`).

---

### 7.4 Suprimentos e fallback

| Tier | Path | operation_id | Uso |
|------|------|--------------|-----|
| B | `GET /supplies/otd` | `get_supplies_otd` | OTD compras — atraso fornecedor |
| C | `GET /supplies/stock-value` | `get_supplies_stock_value` | KPI empresa |
| C | `POST /data/sql` | `execute_readonly_sql` | Último recurso — não na allowlist GPT |

---

## 8. Proposta curada — allowlist ≤30 (`ctx_*`)

Contagem alvo: **28 operações** (margem 2 para evolução).

### Pacote recomendado — investigação por produto / OP / qualidade TOTVS

| # | ctx_* (proposto) | api-delpi operation_id | Motivo |
|---|------------------|------------------------|--------|
| 1 | `ctx_search_products` | `search_products` | Resolver código |
| 2 | `ctx_get_product_detail` | `get_product_detail` | Identificação |
| 3 | `ctx_get_product_summary` | `get_product_summary` | Contexto rápido |
| 4 | `ctx_get_product_structure` | `get_product_structure` | BOM Ishikawa (Material) |
| 5 | `ctx_get_product_structure_exclusivity` | `get_product_structure_exclusivity` | MP exclusiva |
| 6 | `ctx_get_product_guide` | `get_product_guide` | Roteiro (Método/Máquina) |
| 7 | `ctx_get_product_inspection` | `get_product_inspection` | Medição/inspeção QP |
| 8 | `ctx_get_product_production_status` | `get_product_production_status` | OP + apontamentos do PA |
| 9 | `ctx_get_product_factory_status` | `get_product_factory_status` | Visão integrada |
| 10 | `ctx_get_product_shipping_status` | `get_product_shipping_status` | Pós-inspeção final |
| 11 | `ctx_get_product_stock` | `get_product_stock` | Estoque filial |
| 12 | `ctx_get_product_internal_movements` | `get_product_internal_movements` | Rastreio OP/lote |
| 13 | `ctx_get_product_parents` | `get_product_parents` | Onde MP é usada |
| 14 | `ctx_get_product_drawing` | `get_product_drawing` | Desenho técnico |
| 15 | `ctx_get_production_order_by_op` | `get_production_order_by_op` | OP do relato |
| 16 | `ctx_get_production_oee_appointment` | `get_production_oee_appointment_by_id` | Detalhe apontamento |
| 17 | `ctx_list_production_oee` | `get_production_oee` | Buscar apontamentos |
| 18 | `ctx_get_production_schedule_today` | `get_production_schedule_today` | PCP hoje |
| 19 | `ctx_get_production_orders_open` | `get_production_orders_open` | OPs abertas |
| 20 | `ctx_get_production_orders_finished` | `get_production_orders_finished` | OPs finalizadas |
| 21 | `ctx_get_production_planned_vs_real` | `get_production_planned_vs_real_time` | Desvio tempo |
| 22 | `ctx_get_production_losses_records` | `get_production_losses_records` | Refugo detalhado |
| 23 | `ctx_get_production_losses_top_materials` | `get_production_losses_top_materials` | Ranking scrap |
| 24 | `ctx_get_production_consumption_by_item` | `get_production_consumption_by_item` | Consumo MP |
| 25 | `ctx_list_nonconformities` | `list_nonconformities` | NC TOTVS |
| 26 | `ctx_get_inspecoes_entrada_historico` | `get_inspecoes_entrada_historico` | Recebimento MP |
| 27 | `ctx_get_inspecoes_entrada_detalhe` | `get_inspecoes_entrada_historico_detalhe` | Laudo QER |
| 28 | `ctx_get_produced_quantity` | `get_produced_quantity` | Qtd inspeção final |

### Reserva (substituir 2 slots se prioridade mudar)

| Alternativa | Substitui | Quando priorizar |
|-------------|-----------|------------------|
| `ctx_get_product_analyser` | #3 summary | Uma chamada multi-domínio |
| `ctx_list_ppm_internal` | #25 NC list | Foco em indicador PPM |
| `ctx_get_production_allocation_gaps` | #24 consumo | NC de falta de empenho |

### Fase 2 — endpoints compostos (reduzir chamadas, não aumentar GPT ops)

| ctx_* composto | Agrupa |
|----------------|--------|
| `ctx_investigate_product` | detail + structure + guide + production-status |
| `ctx_investigate_production_order` | by-op + oee list + planned-vs-real |
| `ctx_investigate_incoming_quality` | historico + detalhe + rejeitadas-produto |

Implementação: BFF orquestra N chamadas api-delpi; **uma** operação no OpenAPI.

---

## 9. Mapa intenção investigativa → rota

Usar no **Conhecimento** do GPT contexto (espelhar `11-guia-agente-chat.md`).

| Pergunta do analista (exemplo) | Rota primária `ctx_*` | Dados para Ishikawa / 5 Porquês |
|--------------------------------|----------------------|----------------------------------|
| «Qual a estrutura do produto X?» | `ctx_get_product_structure` | Material, componentes |
| «Qual o roteiro de fabricação?» | `ctx_get_product_guide` | Método, Máquina, CT |
| «Quais ensaios QP existem?» | `ctx_get_product_inspection` | Medição |
| «Qual OP e apontamentos do lote?» | `ctx_get_product_production_status` ou `ctx_get_production_order_by_op` | Máquina, Mão de obra, Método |
| «O que foi apontado na operação Y?» | `ctx_get_production_oee_appointment` | Tempos, achados |
| «Houve refugo dessa MP?» | `ctx_get_production_losses_records` | Material, perdas |
| «Consumo real da MP no PA?» | `ctx_get_production_consumption_by_item` | Material |
| «NC semelhante já existe no TOTVS?» | `ctx_list_nonconformities` | Gestão, histórico |
| «Laudo de recebimento da MP?» | `ctx_get_inspecoes_entrada_detalhe` | Material, fornecedor |
| «Saldo em estoque na filial?» | `ctx_get_product_stock` | Material |
| «Desenho técnico do item?» | `ctx_get_product_drawing` | Projeto/engenharia |

**Ordem sugerida no fluxo PAC (após filial + produto confirmados):**

1. `ctx_search_products` / `ctx_get_product_detail`
2. `ctx_get_product_production_status` (se houver lote/OP)
3. `ctx_get_product_structure` + `ctx_get_product_guide`
4. `ctx_list_nonconformities` (mesmo produto, janela 12 meses)
5. Durante 5 Porquês: apontamento, perdas, inspeção entrada conforme hipótese

---

## 10. Relação com o Especialista Qualidade (PAC)

| Capacidade | API |
|------------|-----|
| Abrir/atualizar PAC, Ishikawa, 5 Porquês, ações, evidências | **api-pac-quality** |
| Casos similares, recorrência, padrões de solução | **api-pac-quality** |
| Consultar BOM, OP, apontamento, NC TOTVS, inspeção entrada | **api-pac-context** (novo) |

**Instruções GPT PAC** (sem alterar limite 26): orientar o analista a consultar dados operacionais **antes** de fechar causa — via segundo agente, colagem de resultado, ou (futuro) MCP/action unificada.

**Conhecimento a adicionar** — publicado em `api-pac-context/docs/agente-gpt-import/conhecimento/`:

- `chatgpt-contexto-operacional-guia.md` — mapa §9 + exemplos de perguntas
- `chatgpt-referencia-rotas-ctx.md` — catálogo 28 `ctx_*`
- `chatgpt-distincoes-criticas.md` — inspeção QP vs expedição, roteiro vs PCP, NC PAC vs TOTVS
- Atualizar `chatgpt-conhecimento-regras-gravacao.md` (api-pac-quality) — «consultar contexto ERP quando produto/OP/lote conhecidos»

---

## 11. Fases de implementação

| Fase | Entrega | Critério de aceite |
|------|---------|-------------------|
| **P0** | Este playbook aprovado + allowlist §8 congelada | Produto e arquitetura alinhados |
| **P1** | Repo `api-pac-context`: health, auth, gateway S2S, 10 rotas Tier A produto | Homologação H1: `ctx_get_product_structure` + `ctx_get_product_production_status` |
| **P2** | +18 rotas produção/qualidade; OpenAPI ≤30; gate CI | Import OpenAPI em GPT de homologação (**28 ops publicadas**) |
| **P3** | Composites §8 fase 2; doc Conhecimento GPT | Redução média de tool calls por turno |
| **P4** | (Opcional) Unificar orquestração PAC + contexto | Só se plataforma permitir multi-schema ou MCP |

**Checklist técnico (espelhar api-pac-quality):**

- [x] `contrato-http-api-pac-context-api-delpi.md` (em `api-pac-context/docs/`)
- [x] `scripts/audit_ctx_openapi_operation_limit.py --check`
- [x] Testes delegação: path/query repassados; 404/503 mapeados (P1–P2)
- [x] Pacote Conhecimento GPT: `api-pac-context/docs/agente-gpt-import/`
- [ ] Subdomínio Cloudflare (ex.: `pac-context-api.minhadelpi.com.br`)
- [x] Rotas api-delpi já têm `route_contract_registry` + smoke — **não** criar SQL novo na BFF

---

## 12. Riscos e mitigações

| Risco | Mitigação |
|-------|-----------|
| GPT chama 10 rotas por turno (latência/custo) | Composites P3; instrução «máx. 3 consultas por hipótese» |
| Divergência OpenAPI api-delpi vs ctx_* | Teste contrato + reimport após deploy api-delpi |
| Segunda chave API vazada | Rotação independente; só leitura; sem escrita PAC |
| Duplicar inteligência do chat Minha DELPI | Escopo explícito: agente **externo** GPT; chat interno inalterado |

---

## 13. Referências

| Documento | Local |
|-----------|--------|
| Contrato respostas api-delpi | `delpi-central/minha-delpi-ai-api/docs/roadmap/playbook-10-contrato-respostas-api-delpi.md` |
| Rotas operacionais produção | `delpi-central/minha-delpi-ai-api/docs/roadmap/playbook-15-rotas-operacionais-sem-sql.md` |
| Produtos api-delpi | `delpi-central/api-delpi/docs/api/02-produtos.md` |
| Produção operacional | `delpi-central/api-delpi/docs/api/13-producao-operacional.md` |
| PAC api-delpi | `delpi-central/api-delpi/docs/api/quality-action-plans-pac.md` |
| Guia agente rotas | `delpi-central/api-delpi/docs/api/11-guia-agente-chat.md` |
| Referência endpoints | `delpi-central/api-delpi/docs/api/10-referencia-rapida-endpoints.md` |
| Setup GPT PAC | [chatgpt-especialista-qualidade.md](chatgpt-especialista-qualidade.md) |

---

## 14. Próximos passos

1. **Validar** allowlist §8 com qualidade/planejamento (28 rotas).
2. **Decidir** estratégia §4 (S1 segundo GPT vs aguardar MCP).
3. **Criar** repositório `api-pac-context` espelhando bootstrap api-pac-quality (P1).
4. **Publicar** guia Conhecimento para o agente quando OpenAPI estiver em homologação.
