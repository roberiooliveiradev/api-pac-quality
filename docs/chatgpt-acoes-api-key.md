# ChatGPT Custom GPT — Actions com chave API

Guia para conectar o **GPT Customizado** (ChatGPT workspace) à API PAC via **Chave API / Bearer**, sem JWT Keycloak por usuário.

**URL da API:** `https://pac-api.minhadelpi.com.br`

---

## 1. Gerar e configurar a chave no servidor

No **srv-api**:

```bash
openssl rand -hex 32
```

Adicione em `~/projetos/api-pac-quality/.env`:

```env
PAC_QUALITY_API_KEY=cole_o_token_gerado_aqui
```

Recrie a API:

```bash
cd ~/projetos/api-pac-quality
git pull
docker compose up -d --force-recreate api-pac-quality
```

Teste:

```bash
curl -s -H "Authorization: Bearer SEU_TOKEN" \
  https://pac-api.minhadelpi.com.br/quality/action-plans?page_size=1
```

Sem token → `401`. Com token → `200` (ou lista vazia).

---

## 2. Schema OpenAPI no GPT

No builder do GPT → **Configurar** → **Ações** → **Criar nova ação** (ou editar):

1. **Importar schema** — **Importar de URL:**
   `https://pac-api.minhadelpi.com.br/openapi.json`

   A API PAC publica **26 operações** (fluxo analista). Limite ChatGPT: 30. Coordenação e admin ficam no plugin Minha DELPI.
2. Confirme o servidor:
   ```json
   "url": "https://pac-api.minhadelpi.com.br"
   ```
3. O schema já declara `security: PacApiKey` (Bearer).

> Não use `api.transformamaisdelpi.com.br` — esse é outro serviço. A PAC é só `pac-api.minhadelpi.com.br`.

---

## 3. Autenticação (como na sua tela)

| Campo | Valor |
|-------|--------|
| **Tipo de autenticação** | Chave API |
| **Chave API** | o mesmo valor de `PAC_QUALITY_API_KEY` |
| **Como enviar** | **Bearer** |

Equivale a:

```http
Authorization: Bearer <PAC_QUALITY_API_KEY>
```

Alternativa suportada pela API (se o GPT permitir header customizado):

```http
X-Api-Key: <PAC_QUALITY_API_KEY>
```

Salve a ação.

---

## 4. Instruções recomendadas no GPT (system)

Prompt completo (descrição, instruções, quebra-gelos e checklist): **[chatgpt-especialista-qualidade.md](chatgpt-especialista-qualidade.md)**.

Resumo das regras obrigatórias:

- Não inventar causa raiz; confirmar com o analista antes de gravar.
- **Sempre** apresentar causa raiz provável e **nível de confiança %** após Ishikawa/5 Porquês (requisito liderança jun/2026).
- Se confiança &lt; 70%, listar o que falta levantar para aumentar a confiabilidade.
- Usar `search_similar_cases` antes de concluir causa.
- Escritas (`POST`/`PUT`/`PATCH`) só após confirmação explícita do usuário.
- Diferenciar fato, hipótese e sugestão.
- Registrar no chat quais casos históricos embasaram a sugestão.

(Ver playbook `playbook_pac_qualidade_delpi.md` — regra de ouro.)

---

## 5. Rotas disponíveis (resumo)

Atualizado jun/2026 — paridade com api-delpi (escrita + leituras de governança).

| Intenção | operationId | Método |
|----------|-------------|--------|
| Criar plano | `pac_create_action_plan` | POST |
| Listar planos | `pac_list_action_plans` | GET — query opcional `code=PAC-2026-NNNN` |
| Detalhe | `pac_get_action_plan` | GET — path aceita UUID ou código `PAC-YYYY-NNNN` |
| Atualizar plano | `pac_update_action_plan` | PATCH |
| Atualizar status | `pac_update_action_plan_status` | PATCH |
| Reabrir plano | `pac_reopen_action_plan` | POST |
| Ishikawa | `pac_upsert_ishikawa` | PUT |
| 5 Porquês | `pac_upsert_five_whys` | PUT |
| Criar ações | `pac_create_plan_actions` | POST |
| Atualizar ação | `pac_update_plan_action` | PATCH |
| Remover ação | `pac_delete_plan_action` | DELETE |
| Submeter eficácia | `pac_submit_effectiveness_review` | POST |
| Eficácia direta | `pac_record_effectiveness_review` | POST |
| Relatório 8D | `pac_upsert_rnc_8d` | PUT |
| Exportar 8D | `pac_export_rnc_8d` | GET (`template_key` opcional: `weg_wfr20997`, `delpi_8d`) |
| Catálogo templates 8D | `pac_list_export_templates` | GET |
| Evidências | `pac_list_plan_evidences` / `pac_attach_plan_evidence` / `pac_delete_plan_evidence` / `pac_download_plan_evidence` | GET / POST multipart / DELETE / GET |
| Casos similares | `pac_search_similar_cases` | POST |
| Padrões de solução | `pac_search_solution_patterns` | POST |
| Sugerir ações | `pac_suggest_actions` | POST |

Rotas de coordenação/admin ficam só no **plugin Minha DELPI** (api-delpi).

Gate CI: `python scripts/audit_pac_openapi_operation_limit.py --check`. Após deploy, **reimporte** `/openapi.json` no GPT.

### Upload de evidência (multipart)

`pac_attach_plan_evidence` exige `multipart/form-data`:

- `file` (obrigatório)
- `evidence_type` (obrigatório)
- `section`, `description`, `knowledge_visible`, `action_id` (opcionais)

Ver detalhes em [chatgpt-especialista-qualidade.md](chatgpt-especialista-qualidade.md) § Upload de evidências.

---

## 6. Segurança (poucos usuários)

| Prática | Motivo |
|---------|--------|
| Token longo (`openssl rand -hex 32`) | Dificulta brute force |
| Só compartilhar GPT com usuários autorizados | A chave fica no GPT, não por usuário |
| Rotacionar `PAC_QUALITY_API_KEY` se vazar | Gere novo token + atualize `.env` e GPT |
| Não commitar `.env` | Token é segredo |

A api-pac-quality **não** usa JWT Keycloak — apenas `PAC_QUALITY_API_KEY`. RBAC por usuário fica no plugin Minha DELPI (api-delpi).

---

## 7. Troubleshooting

| Problema | Solução |
|----------|---------|
| `401 Unauthorized` | Token errado ou `PAC_QUALITY_API_KEY` ausente no `.env` |
| `Could not resolve` / host errado | Servidor no schema deve ser `pac-api.minhadelpi.com.br` |
| GPT não chama a API | Verificar se ações estão habilitadas e schema importado sem erro |
| Erro «máximo 30 operações» | API PAC desatualizada — deploy com **26 operações** em `/openapi.json` |
| `422` | Body incompleto — ver campos obrigatórios no schema |

---

Ver também: [chatgpt-especialista-qualidade.md](chatgpt-especialista-qualidade.md) · [cloudflare-subdominio-pac-api.md](cloudflare-subdominio-pac-api.md) · [DEPLOYMENT.md](DEPLOYMENT.md)
