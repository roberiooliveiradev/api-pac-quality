"""Paridade de escrita api-delpi ↔ api-pac-quality (fluxo analista GPT).

Homologação local: validar na api-delpi (`run_h1_api_smoke.py`). Este teste garante que
a api-pac expõe as escritas do analista; coordenação/admin ficam só no plugin.
"""

from __future__ import annotations

from app.interface.http.route_contract_registry import ANALYST_PAC_OPERATION_IDS, ROUTE_CONTRACTS

WRITE_PARITY: dict[str, str] = {
    "create_quality_action_plan": "pac_create_action_plan",
    "update_quality_action_plan": "pac_update_action_plan",
    "update_quality_action_plan_status": "pac_update_action_plan_status",
    "reopen_quality_action_plan": "pac_reopen_action_plan",
    "upsert_quality_action_plan_ishikawa": "pac_upsert_ishikawa",
    "upsert_quality_action_plan_five_whys": "pac_upsert_five_whys",
    "create_quality_action_plan_actions": "pac_create_plan_actions",
    "update_quality_action_plan_action": "pac_update_plan_action",
    "delete_quality_action_plan_action": "pac_delete_plan_action",
    "record_quality_action_plan_effectiveness": "pac_record_effectiveness_review",
    "submit_quality_action_plan_effectiveness_review": "pac_submit_effectiveness_review",
    "upsert_quality_action_plan_rnc_8d": "pac_upsert_rnc_8d",
    "export_quality_action_plan_rnc_8d": "pac_export_rnc_8d",
    "list_quality_action_plan_evidences": "pac_list_plan_evidences",
    "attach_quality_action_plan_evidence": "pac_attach_plan_evidence",
    "update_quality_action_plan_evidence": "pac_update_plan_evidence",
    "delete_quality_action_plan_evidence": "pac_delete_plan_evidence",
    "delete_quality_action_plan": "pac_delete_action_plan",
}

PLUGIN_ONLY_WRITE_PARITY: dict[str, str] = {
    "approve_quality_action_plan_effectiveness_review": "pac_approve_effectiveness_review",
    "reject_quality_action_plan_effectiveness_review": "pac_reject_effectiveness_review",
    "promote_quality_action_plan_solution_pattern": "pac_promote_solution_pattern",
    "dispatch_quality_action_plan_notifications": "pac_dispatch_notifications",
}


def test_pac_registry_has_all_write_parity_operations() -> None:
    missing = sorted(set(WRITE_PARITY.values()) - ROUTE_CONTRACTS.keys())
    assert not missing, f"operation_id PAC ausente no registry: {missing}"


def test_write_parity_includes_onda1_8d_and_evidence() -> None:
    assert WRITE_PARITY["upsert_quality_action_plan_rnc_8d"] == "pac_upsert_rnc_8d"
    assert WRITE_PARITY["attach_quality_action_plan_evidence"] == "pac_attach_plan_evidence"
    assert WRITE_PARITY["update_quality_action_plan"] == "pac_update_action_plan"


def test_write_parity_includes_analyst_effectiveness_flow() -> None:
    assert WRITE_PARITY["reopen_quality_action_plan"] == "pac_reopen_action_plan"
    assert (
        WRITE_PARITY["submit_quality_action_plan_effectiveness_review"]
        == "pac_submit_effectiveness_review"
    )


def test_plugin_only_writes_not_in_pac_openapi() -> None:
    assert set(PLUGIN_ONLY_WRITE_PARITY.values()).isdisjoint(ANALYST_PAC_OPERATION_IDS)
