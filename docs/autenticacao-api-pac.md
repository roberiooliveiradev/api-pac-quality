# Autenticação — API PAC Qualidade

## Princípio

A **api-pac-quality** é uma API **standalone** para o **Custom GPT** (ChatGPT Actions). Ela **não** reutiliza o pacote `delpi_auth` nem JWT Keycloak do Minha DELPI.

| Camada | Autenticação |
|--------|----------------|
| **api-pac-quality** (este repo) | `PAC_QUALITY_API_KEY` — chave de serviço única |
| **api-delpi** + plugin MFE | JWT Keycloak + RBAC (`quality-action-plans.*`) |

Isso reduz superfície de ataque: o agente GPT não herda permissões de usuário nem JWT Keycloak.

**Exceção em runtime:** `pac_search_assignable_users` chama a Core API com `CORE_API_INTEGRATIONS_SERVICE_TOKEN` (S2S). **CRUD transacional** delega sempre à api-delpi (`API_DELPI_BASE_URL` + `API_DELPI_INTERNAL_SERVICE_TOKEN`). Ver [contrato-http-api-pac-api-delpi.md](contrato-http-api-pac-api-delpi.md).

## Como autenticar

Variável de ambiente no servidor:

```env
PAC_QUALITY_API_KEY=<token-longo>
```

Gerar token:

```bash
openssl rand -hex 32
```

Headers aceitos nas rotas protegidas:

```http
Authorization: Bearer <PAC_QUALITY_API_KEY>
```

ou

```http
X-Api-Key: <PAC_QUALITY_API_KEY>
```

Rotas públicas (sem chave): `/health`, `/openapi.json`, `/docs`, `/redoc`.

## Fluxo no código

```
Request
  → pac_auth_middleware
      → is_public_path? → segue
      → request_has_valid_pac_api_key? → 401
      → set_pac_authenticated_actor(PAC_GPT_AGENT_ACTOR)
  → handler da rota (sem @require_permission)
```

Módulos:

| Arquivo | Responsabilidade |
|---------|------------------|
| `app/interface/http/middleware/pac_api_key.py` | Comparação segura do token (`secrets.compare_digest`) |
| `app/interface/http/middleware/pac_auth_middleware.py` | Middleware HTTP único |
| `app/interface/http/middleware/pac_public_paths.py` | Paths públicos |
| `app/interface/http/middleware/pac_request_context.py` | Ator `pac-gpt-agent` em context var |

`created_by_user_id` / `updated_by` nas escritas usam `pac-gpt-agent` (ou ator propagado via headers `X-Delpi-Actor-*` na api-delpi quando delegado). Vínculo humano para fila: `responsible_user_id` nas ações e `member_user_id` na equipe 8D — obter UUID com `pac_search_assignable_users`.

## RBAC e plugin

Códigos `quality-action-plans.*` em `app/application/security/pac_quality_permissions.py` são **referência** para o plugin na api-delpi — **não** são checados nesta API.

Funcionalidades que exigem perfil de coordenação (aprovar eficácia, audit log, fila pendente, etc.) **não** estão expostas na api-pac-quality; use o plugin Minha DELPI.

## Build e dependências

- **Dockerfile** não copia `delpi-central/shared`
- **requirements.txt** sem `PyJWT` / `python-jose`
- CI (`scripts/ci-smoke.sh`) não precisa de `PYTHONPATH` para `delpi_auth`

## ChatGPT Custom GPT

1. Actions → importar `https://pac-api.minhadelpi.com.br/openapi.json`
2. Autenticação → Chave API → Bearer (mesmo valor de `PAC_QUALITY_API_KEY`)
3. Rotacionar chave: atualizar `.env` no srv-api **e** no builder do GPT

Guias: [chatgpt-acoes-api-key.md](chatgpt-acoes-api-key.md) · [chatgpt-especialista-qualidade.md](chatgpt-especialista-qualidade.md)

## Troubleshooting

| Sintoma | Causa provável |
|---------|----------------|
| `401` em todas as rotas | `PAC_QUALITY_API_KEY` ausente no `.env` ou token errado no GPT |
| `401` só em produção | Deploy sem recriar container após alterar `.env` |
| GPT não envia Bearer | Reconfigurar Actions → tipo Chave API → Bearer |

## Ver também

- [openapi-analista-24-operacoes.md](openapi-analista-24-operacoes.md) — **26 operações** no OpenAPI publicado
- [DEPLOYMENT.md](DEPLOYMENT.md) — deploy no srv-api
