"""Rotas Onda 1 — registry api-pac pronto para deploy H2."""

from __future__ import annotations

from app.interface.http.route_contract_registry import ROUTE_CONTRACTS

ONDA1_PAC_OPERATION_IDS = frozenset(
    {
        "pac_create_action_plan",
        "pac_list_action_plans",
        "pac_get_action_plan",
        "pac_update_action_plan",
        "pac_update_action_plan_status",
        "pac_upsert_ishikawa",
        "pac_upsert_five_whys",
        "pac_create_plan_actions",
        "pac_update_plan_action",
        "pac_record_effectiveness_review",
        "pac_upsert_rnc_8d",
        "pac_export_rnc_8d",
        "pac_list_plan_evidences",
        "pac_attach_plan_evidence",
        "pac_delete_plan_evidence",
        "pac_search_similar_cases",
        "pac_search_solution_patterns",
        "pac_suggest_actions",
    }
)


def test_onda1_pac_operation_ids_registered_for_gpt_agent():
    missing = sorted(ONDA1_PAC_OPERATION_IDS - ROUTE_CONTRACTS.keys())
    assert not missing, f"operation_id Onda 1 ausente no registry PAC: {missing}"


def test_onda1_8d_and_intelligence_contract_entities():
    assert ROUTE_CONTRACTS["pac_upsert_rnc_8d"].entity == "quality_action_plan_rnc_8d"
    assert ROUTE_CONTRACTS["pac_search_similar_cases"].entity == "pac_quality_similar_cases"
