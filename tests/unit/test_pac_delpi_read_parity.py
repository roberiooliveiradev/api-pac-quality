"""Paridade de leitura api-delpi ↔ api-pac-quality (fluxo analista GPT)."""

from __future__ import annotations

from app.interface.http.route_contract_registry import ANALYST_PAC_OPERATION_IDS, ROUTE_CONTRACTS

# Leituras expostas ao agente GPT (analista).
READ_PARITY: dict[str, str] = {
    "list_quality_action_plans": "pac_list_action_plans",
    "get_quality_action_plan_detail": "pac_get_action_plan",
    "list_quality_action_plan_evidences": "pac_list_plan_evidences",
    "list_quality_action_plan_export_templates": "pac_list_export_templates",
    "get_quality_action_plan_evidence_content": "pac_get_plan_evidence_content",
    "export_quality_action_plan_rnc_8d": "pac_export_rnc_8d",
}

# Somente plugin Minha DELPI (api-delpi) — não expor na api-pac-quality.
PLUGIN_ONLY_READ_PARITY: dict[str, str] = {
    "list_quality_action_plan_pending_effectiveness_reviews": (
        "pac_list_pending_effectiveness_reviews"
    ),
    "list_quality_action_plan_audit_log": "pac_list_plan_audit_log",
    "list_quality_action_plan_revisions": "pac_list_plan_revisions",
    "get_quality_action_plan_revision": "pac_get_plan_revision",
}


def test_pac_registry_has_all_read_parity_operations() -> None:
    missing = sorted(set(READ_PARITY.values()) - ROUTE_CONTRACTS.keys())
    assert not missing, f"operation_id PAC ausente no registry: {missing}"


def test_plugin_only_reads_not_in_pac_openapi() -> None:
    assert set(PLUGIN_ONLY_READ_PARITY.values()).isdisjoint(ANALYST_PAC_OPERATION_IDS)
