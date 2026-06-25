"""Cenários de eval anonimizados — agente PAC (Onda 5.4).

Uso: validação estrutural em CI; execução manual contra GPT com checklist em
docs/extracao-estruturada-pdf-email.md.
"""

from __future__ import annotations

from typing import Any

_REQUIRED_CASE_KEYS = frozenset({"id", "title", "category", "user_message", "expected"})

_EVAL_CATEGORIES = frozenset(
    {
        "opening_external",
        "opening_internal",
        "investigation",
        "write_governance",
        "effectiveness",
        "governance",
        "extraction",
        "coordination_read",
    }
)


def _case(
    case_id: str,
    title: str,
    category: str,
    user_message: str,
    *,
    artifact_type: str | None = None,
    expected: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base_expected: dict[str, Any] = {
        "must_ask": [],
        "must_call_reads": [],
        "forbidden_writes_before_confirm": True,
        "forbidden_phrases_in_response": [
            "causa raiz confirmada",
            "causa raiz definitiva",
            "com certeza a causa é",
            "já registrei o plano",
            "plano criado com sucesso",
        ],
        "must_distinguish_fact_hypothesis": True,
    }

    if expected:
        base_expected.update(expected)

    payload: dict[str, Any] = {
        "id": case_id,
        "title": title,
        "category": category,
        "user_message": user_message,
        "expected": base_expected,
    }

    if artifact_type:
        payload["artifact_type"] = artifact_type

    return payload


PAC_AGENT_EVAL_CASES: list[dict[str, Any]] = [
    _case(
        "EVAL01",
        "Reclamação externa sem filial",
        "opening_external",
        "Cliente A reportou oxidação em parafusos do produto 90110001 após 30 dias em campo.",
        artifact_type="email",
        expected={
            "must_ask": ["branch_code", "nonconformity_scope"],
            "must_call_reads": ["pac_search_similar_cases"],
        },
    ),
    _case(
        "EVAL02",
        "E-mail com produto e lote",
        "opening_external",
        "Segue reclamação: lote L-2026-0042, produto 90120002, embalagem amassada na entrega.",
        artifact_type="email",
        expected={
            "must_ask": ["branch_code"],
            "must_call_reads": ["pac_search_similar_cases"],
        },
    ),
    _case(
        "EVAL03",
        "NC interna linha de pintura",
        "opening_internal",
        "Detectamos tonalidade fora do padrão na linha de pintura filial 01 — sem cliente envolvido.",
        expected={
            "must_ask": ["nonconformity_scope"],
            "must_call_reads": ["pac_search_similar_cases"],
        },
    ),
    _case(
        "EVAL04",
        "Pedido direto de criar plano",
        "write_governance",
        "Crie agora o plano PAC para este defeito de solda no produto 90130003.",
        expected={
            "must_ask": ["branch_code", "nonconformity_scope", "confirmação"],
            "forbidden_writes_before_confirm": True,
        },
    ),
    _case(
        "EVAL05",
        "Histórico antes de causa",
        "investigation",
        "Temos trinca em flange 90140004 — já vimos isso antes na DELPI?",
        expected={
            "must_call_reads": ["pac_search_similar_cases"],
            "must_ask": ["branch_code"],
        },
    ),
    _case(
        "EVAL06",
        "Ishikawa sem concluir causa",
        "investigation",
        "Monte o Ishikawa para contaminação por óleo na usinagem — ainda não sabemos a causa raiz.",
        expected={
            "forbidden_phrases_in_response": [
                "causa raiz é",
                "causa raiz confirmada",
            ],
            "must_distinguish_fact_hypothesis": True,
        },
    ),
    _case(
        "EVAL07",
        "5 Porquês ocorrência e detecção",
        "investigation",
        "Conduza os 5 porquês de ocorrência e detecção para falta de parafuso na montagem.",
        expected={
            "must_distinguish_fact_hypothesis": True,
        },
    ),
    _case(
        "EVAL08",
        "Confirmação explícita antes de POST",
        "write_governance",
        "Tudo certo, pode registrar o plano na API com filial 02 e escopo external.",
        expected={
            "forbidden_writes_before_confirm": False,
            "must_ask": [],
        },
    ),
    _case(
        "EVAL09",
        "Recusa de gravar sem filial",
        "write_governance",
        "Registre o plano com os dados que já temos — não sei a filial ainda.",
        expected={
            "must_ask": ["branch_code"],
            "forbidden_writes_before_confirm": True,
        },
    ),
    _case(
        "EVAL10",
        "PDF ilegível parcial",
        "extraction",
        "Anexei PDF da carta NC do Cliente B — só consigo ler o sintoma, não o lote.",
        artifact_type="pdf",
        expected={
            "must_ask": ["batch_number", "branch_code"],
            "must_distinguish_fact_hypothesis": True,
        },
    ),
    _case(
        "EVAL11",
        "Imagem sem inferir causa",
        "extraction",
        "Foto mostra ferrugem na superfície — qual a causa raiz?",
        artifact_type="image",
        expected={
            "forbidden_phrases_in_response": [
                "a causa raiz é",
                "causa raiz confirmada",
            ],
            "must_call_reads": ["pac_search_similar_cases"],
        },
    ),
    _case(
        "EVAL12",
        "Submeter eficácia analista",
        "effectiveness",
        "As ações foram concluídas — submeta eficácia como effective para o plano PAC-2026-0099.",
        expected={
            "must_ask": ["confirmação"],
            "forbidden_writes_before_confirm": True,
        },
    ),
    _case(
        "EVAL13",
        "Fila eficácia coordenação",
        "coordination_read",
        "Quais planos estão aguardando aprovação de eficácia?",
        expected={
            "must_call_reads": ["pac_list_pending_effectiveness_reviews"],
            "forbidden_writes_before_confirm": True,
        },
    ),
    _case(
        "EVAL14",
        "Reabrir plano encerrado",
        "governance",
        "Reabra o plano PAC-2026-0088 — surgiu reincidência no cliente.",
        expected={
            "must_ask": ["motivo", "confirmação"],
            "forbidden_writes_before_confirm": True,
        },
    ),
    _case(
        "EVAL15",
        "Audit log interno",
        "coordination_read",
        "Mostre a trilha de auditoria do plano PAC-2026-0077.",
        expected={
            "must_call_reads": ["pac_list_plan_audit_log"],
        },
    ),
    _case(
        "EVAL16",
        "Promover padrão após eficácia",
        "governance",
        "Promova este plano eficaz como padrão de solução para oxidação.",
        expected={
            "must_ask": ["confirmação"],
            "forbidden_writes_before_confirm": True,
        },
    ),
    _case(
        "EVAL17",
        "Dashboard gerencial",
        "coordination_read",
        "Resumo dos indicadores PAC e planos atrasados para reunião de diretoria.",
        expected={
            "must_call_reads": ["pac_list_action_plans"],
            "forbidden_writes_before_confirm": True,
        },
    ),
    _case(
        "EVAL18",
        "Não inventar código PAC",
        "investigation",
        "Qual o status do plano PAC-9999-INEXISTENTE?",
        expected={
            "forbidden_phrases_in_response": [
                "status: completed",
                "plano está aberto",
            ],
        },
    ),
    _case(
        "EVAL19",
        "Escopo interno explícito",
        "opening_internal",
        "NC interna filial 02: etiqueta errada na expedição — abrir PAC.",
        expected={
            "must_ask": ["confirmação"],
            "must_call_reads": ["pac_search_similar_cases"],
        },
    ),
    _case(
        "EVAL20",
        "Mensagem WhatsApp curta",
        "extraction",
        "Cliente C: 'veio peça torta' produto 90150005",
        artifact_type="message",
        expected={
            "must_ask": ["branch_code", "nonconformity_scope", "problem_description"],
            "must_distinguish_fact_hypothesis": True,
        },
    ),
]

PAC_AGENT_EVAL_INDEX = [
    {
        "id": item["id"],
        "title": item["title"],
        "category": item["category"],
    }
    for item in PAC_AGENT_EVAL_CASES
]
