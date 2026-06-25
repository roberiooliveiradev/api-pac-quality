"""Paridade de leitura api-delpi ↔ api-pac-quality (consultas do agente GPT)."""

from __future__ import annotations

from app.interface.http.route_contract_registry import ROUTE_CONTRACTS

READ_PARITY: dict[str, str] = {
    "list_quality_action_plans": "pac_list_action_plans",
    "get_quality_action_plan_detail": "pac_get_action_plan",
    "list_quality_action_plan_pending_effectiveness_reviews": (
        "pac_list_pending_effectiveness_reviews"
    ),
    "list_quality_action_plan_audit_log": "pac_list_plan_audit_log",
    "list_quality_action_plan_evidences": "pac_list_plan_evidences",
    "export_quality_action_plan_rnc_8d": "pac_export_rnc_8d",
}


def test_pac_registry_has_all_read_parity_operations() -> None:
    missing = sorted(set(READ_PARITY.values()) - ROUTE_CONTRACTS.keys())
    assert not missing, f"operation_id PAC ausente no registry: {missing}"
