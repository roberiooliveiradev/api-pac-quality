"""Evals anonimizados do agente PAC — Onda 5.4."""

from __future__ import annotations

from app.domain.services.pac_agent_eval_policy_service import PacAgentEvalPolicyService
from tests.fixtures.pac_agent_eval_cases import PAC_AGENT_EVAL_CASES, PAC_AGENT_EVAL_INDEX


def test_eval_catalog_has_twenty_anonymized_cases() -> None:
    assert len(PAC_AGENT_EVAL_CASES) == 20
    assert len(PAC_AGENT_EVAL_INDEX) == 20


def test_eval_catalog_passes_policy_validation() -> None:
    errors = PacAgentEvalPolicyService.validate_catalog(PAC_AGENT_EVAL_CASES)

    assert errors == [], f"erros no catálogo: {errors}"


def test_eval_policy_rejects_invented_root_cause_response() -> None:
    case = next(item for item in PAC_AGENT_EVAL_CASES if item["id"] == "EVAL06")
    bad = "A causa raiz confirmada é contaminação por óleo na usinagem."

    result = PacAgentEvalPolicyService.evaluate_response(case, bad)

    assert result.passed is False
    assert result.violations


def test_eval_policy_accepts_hypothesis_marked_response() -> None:
    case = next(item for item in PAC_AGENT_EVAL_CASES if item["id"] == "EVAL06")
    good = (
        "**Hipótese:** contaminação por óleo na usinagem — precisamos validar com o analista. "
        "Sugestão: conduzir Ishikawa antes de concluir."
    )

    result = PacAgentEvalPolicyService.evaluate_response(case, good)

    assert result.passed is True
    assert not result.violations


def test_eval_policy_blocks_write_without_confirmation() -> None:
    case = next(item for item in PAC_AGENT_EVAL_CASES if item["id"] == "EVAL04")

    result = PacAgentEvalPolicyService.evaluate_response(
        case,
        "Registrei na API com pac_create_action_plan.",
    )

    assert result.passed is False


def test_eval_policy_requires_branch_question() -> None:
    case = next(item for item in PAC_AGENT_EVAL_CASES if item["id"] == "EVAL01")

    result = PacAgentEvalPolicyService.evaluate_response(
        case,
        "Vou buscar casos similares. O defeito parece ser oxidação.",
    )

    assert result.passed is False
    assert any("filial" in item for item in result.violations)
