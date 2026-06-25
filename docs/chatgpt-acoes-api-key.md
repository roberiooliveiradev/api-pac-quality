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

   O schema é gerado pelo FastAPI (mesmo padrão da api-delpi). Inclui `security: PacApiKey` (Bearer) e `servers` quando `PUBLIC_BASE_URL` está configurado.
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
- Usar `search_similar_cases` antes de concluir causa.
- Escritas (`POST`/`PUT`/`PATCH`) só após confirmação explícita do usuário.
- Diferenciar fato, hipótese e sugestão.
- Registrar no chat quais casos históricos embasaram a sugestão.

(Ver playbook `playbook_pac_qualidade_delpi.md` — regra de ouro.)

---

## 5. Rotas disponíveis (resumo)

| Intenção | operationId |
|----------|-------------|
| Criar plano | `pac_create_action_plan` |
| Listar planos | `pac_list_action_plans` |
| Detalhe | `pac_get_action_plan` |
| Atualizar plano | `pac_update_action_plan` |
| Ishikawa | `pac_upsert_ishikawa` |
| 5 Porquês | `pac_upsert_five_whys` |
| Criar ações | `pac_create_plan_actions` |
| Relatório 8D | `pac_upsert_rnc_8d` |
| Exportar 8D | `pac_export_rnc_8d` |
| Evidências | `pac_list_plan_evidences` / `pac_attach_plan_evidence` |
| Casos similares | `pac_search_similar_cases` |
| Padrões de solução | `pac_search_solution_patterns` |
| Sugerir ações | `pac_suggest_actions` |

Lista completa no OpenAPI.

---

## 6. Segurança (poucos usuários)

| Prática | Motivo |
|---------|--------|
| Token longo (`openssl rand -hex 32`) | Dificulta brute force |
| Só compartilhar GPT com usuários autorizados | A chave fica no GPT, não por usuário |
| Rotacionar `PAC_QUALITY_API_KEY` se vazar | Gere novo token + atualize `.env` e GPT |
| Não commitar `.env` | Token é segredo |
| Restringir quem edita o GPT no workspace | Quem edita vê a chave nas Actions |

A API ainda aceita **JWT Keycloak** (Minha DELPI) se no futuro usar o chat interno com `authMode: user_token`.

---

## 7. Troubleshooting

| Problema | Solução |
|----------|---------|
| `401 Unauthorized` | Token errado ou `PAC_QUALITY_API_KEY` ausente no `.env` |
| `Could not resolve` / host errado | Servidor no schema deve ser `pac-api.minhadelpi.com.br` |
| GPT não chama a API | Verificar se ações estão habilitadas e schema importado sem erro |
| `422` | Body incompleto — ver campos obrigatórios no schema |

---

Ver também: [chatgpt-especialista-qualidade.md](chatgpt-especialista-qualidade.md) · [cloudflare-subdominio-pac-api.md](cloudflare-subdominio-pac-api.md) · [DEPLOYMENT.md](DEPLOYMENT.md)
