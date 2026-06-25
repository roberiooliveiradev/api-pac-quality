# Extração estruturada — PDF, e-mail e mensagem (Onda 5.3)

Guia para o **Especialista Qualidade** (GPT e Minha DELPI Chat) ao receber relato em anexo ou texto colado.

**Regra:** extrair → classificar (FATO / SUGESTÃO) → validar lacunas com o analista → **só então** gravar na API.

---

## 1. Campos alvo (`draft_extraction`)

| Campo | Obrigatório no plano | Origem típica | Notas |
|-------|---------------------|---------------|--------|
| `problem_description` | Sim | Corpo e-mail, PDF, chat | Sintoma objetivo |
| `branch_code` | Sim (`01` \| `02`) | Assunto, rodapé, pergunta ao analista | **Nunca** inferir só pelo CEP |
| `nonconformity_scope` | Sim (`internal` \| `external`) | Contexto do relato | Não confundir com `source_type` |
| `customer_name` | Externa | Cabeçalho e-mail, carta NC | Anonimizar em evals |
| `customer_contact` | Não | Assinatura e-mail | |
| `product_code` | Recomendado | NF, etiqueta, desenho | Validar formato com analista |
| `batch_number` | Recomendado | NF, lote, OP | |
| `detected_at` | Não | Data do relato | ISO ou confirmar com analista |
| `severity` | Não | Urgência do texto | `low` … `critical` — sugestão |
| `source_type` | Não | Canal | `email`, `pdf`, `message`, … |
| `source_reference` | Não | Protocolo cliente | Só se informado |

---

## 2. JSON de rascunho (validação humana)

O agente monta um rascunho **antes** de `pac_create_action_plan`:

```json
{
  "draft_extraction": {
    "problem_description": "Oxidação em parafusos após 30 dias em campo",
    "branch_code": null,
    "nonconformity_scope": "external",
    "customer_name": "Cliente A (sugerido do e-mail)",
    "product_code": "90123456 (sugerido — confirmar)",
    "batch_number": null,
    "severity": "high",
    "source_type": "email",
    "fields_confidence": {
      "problem_description": "high",
      "branch_code": "missing",
      "nonconformity_scope": "medium",
      "product_code": "low"
    }
  },
  "labeled_facts": ["Reclamação recebida em 2026-06-10"],
  "labeled_hypotheses": ["Possível falha de tratamento superficial"],
  "missing_critical": ["branch_code", "batch_number"]
}
```

**Validação humana obrigatória** quando `missing_critical` não estiver vazio ou qualquer `fields_confidence` for `low` / `missing` em campo obrigatório.

---

## 3. Fluxo por tipo de entrada

### E-mail

1. Extrair assunto + corpo (ignorar disclaimers longos).
2. Identificar remetente → `customer_name` / `customer_contact` (FATO se explícito).
3. Buscar produto/lote em tabelas ou anexos referenciados.
4. Perguntar filial e escopo se ambíguos.
5. Anexar original: `pac_attach_plan_evidence` com `evidence_type: email` **após** criar plano.

### PDF (carta NC, relatório cliente)

1. OCR/texto: problema, produto, lote, data.
2. Marcar ilegível como `missing` — não preencher com suposição.
3. `source_type: pdf`; evidência na seção `nc_description` ou `attachments`.

### Imagem (foto do defeito)

1. Descrever só o visível — defeito, localização, quantidade aparente.
2. Não inferir causa raiz pela imagem.
3. `evidence_type: image`; causa raiz continua em Ishikawa / 5 Porquês.
4. **Tags sugeridas (Onda 6.3):** `pac_suggest_evidence_tags` com `ocr_text` (visão do GPT) ou `pac_suggest_evidence_tags_from_image` (OCR local com `PAC_EVIDENCE_OCR_ENABLED=true`). Validar `suggested_symptom_tags` com o analista antes de gravar no plano.

---

## 4. Checklist antes de gravar

- [ ] `branch_code` confirmado pelo analista
- [ ] `nonconformity_scope` confirmado
- [ ] `problem_description` sem misturar hipótese como fato
- [ ] Histórico consultado (`pac_search_similar_cases`) se problema minimamente descrito
- [ ] Confirmação explícita (“pode registrar”) recebida
- [ ] Evidência anexada quando o procedimento exigir

---

## 5. Evals e CI

Cenários anonimizados: `tests/fixtures/pac_agent_eval_cases.py` (Onda 5.4).

```bash
cd api-pac-quality
.venv/bin/python scripts/run_pac_agent_eval.py --check-catalog
.venv/bin/pytest tests/unit/test_pac_agent_eval_cases.py -q
```

Ver também: [chatgpt-especialista-qualidade.md](chatgpt-especialista-qualidade.md) § 2 (fluxo obrigatório).
