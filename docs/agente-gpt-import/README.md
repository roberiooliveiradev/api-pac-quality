# Importação — Especialista Qualidade (Custom GPT)

Pacote **somente** do que entra no builder do ChatGPT. Documentação operacional (deploy, Cloudflare, contrato api-delpi) permanece em `docs/` na raiz.

Guia completo de configuração: [`../chatgpt-especialista-qualidade.md`](../chatgpt-especialista-qualidade.md)

---

## Checklist rápido

| Onde no builder | O que fazer | Arquivos desta pasta |
|-----------------|-------------|----------------------|
| **Descrição** | Colar texto sugerido | Ver §1 em `chatgpt-especialista-qualidade.md` |
| **Instruções** | Copiar/colar (≤ 8.000 caracteres) | [`instrucoes/chatgpt-instrucoes-system-prompt.txt`](instrucoes/chatgpt-instrucoes-system-prompt.txt) |
| **Conhecimento** | Upload de **todos** os arquivos da pasta | Tudo em [`conhecimento/`](conhecimento/) |
| **Actions** | Importar OpenAPI por URL (não é arquivo local) | `https://pac-api.minhadelpi.com.br/openapi.json` + Bearer |

---

## Instruções (`instrucoes/`)

| Arquivo | Uso |
|---------|-----|
| `chatgpt-instrucoes-system-prompt.txt` | Colar integralmente no campo **Instruções** — **não** fazer upload em Conhecimento |

---

## Conhecimento (`conhecimento/`)

Fazer upload de **cada** arquivo abaixo no campo **Conhecimento** do builder:

| Arquivo | Conteúdo |
|---------|----------|
| `chatgpt-conhecimento-regras-gravacao.md` | Checklist de gravação, causa raiz + confiança %, glossário PT-BR, erros frequentes |
| `chatgpt-referencia-campos-api.md` | Campos PAC, contatos cliente/DELPI, cabeçalho material/NF (`template_payload`), evidências, 5 Porquês |
| `extracao-estruturada-pdf-email.md` | Rascunho de extração de PDF/e-mail antes do create |
| `entrevista-ishikawa.md` | Roteiro 6M (antes dos Porquês) |
| `entrevista-cinco-porques.md` | Roteiro 5 Porquês (após Ishikawa) |

**Opcional — contexto ERP (Protheus):** se o GPT tiver Action da **api-pac-context**, faça upload também dos 3 arquivos em `api-pac-context/docs/agente-gpt-import/conhecimento/` (`chatgpt-contexto-operacional-guia.md`, `chatgpt-referencia-rotas-ctx.md`, `chatgpt-distincoes-criticas.md`). Ver `chatgpt-conhecimento-regras-gravacao.md` §5 (contexto ERP).

---

## O que **não** importar no agente

Ficam em `docs/` (referência humana / infra):

- `chatgpt-especialista-qualidade.md` — manual de setup
- `chatgpt-acoes-api-key.md` — chave API e Actions
- `DEPLOYMENT.md`, `cloudflare-subdominio-pac-api.md`, `contrato-http-api-pac-api-delpi.md`, etc.

---

## Após alteração neste repositório

1. Atualizar **Instruções** se mudou `instrucoes/chatgpt-instrucoes-system-prompt.txt`
2. Reenviar arquivos alterados em **Conhecimento**
3. Reimportar `/openapi.json` se a API PAC foi publicada com rotas novas
