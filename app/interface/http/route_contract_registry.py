"""Contratos semânticos (operationId → entity/shape) para meta / x-delpi — Playbook 22."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RouteContract:
    entity: str
    shape: str


ROUTE_CONTRACTS: dict[str, RouteContract] = {
    "pac_create_action_plan": RouteContract("quality_action_plan", "scalar"),
    "pac_list_action_plans": RouteContract("quality_action_plan", "paged_list"),
    "pac_get_action_plan": RouteContract("quality_action_plan", "composite_analysis"),
    "pac_update_action_plan": RouteContract("quality_action_plan", "scalar"),
    "pac_update_action_plan_status": RouteContract("quality_action_plan", "scalar"),
    "pac_upsert_ishikawa": RouteContract("quality_action_plan_ishikawa", "scalar"),
    "pac_upsert_five_whys": RouteContract("quality_action_plan_five_whys", "scalar"),
    "pac_create_plan_actions": RouteContract("quality_action_plan_action", "paged_list"),
    "pac_update_plan_action": RouteContract("quality_action_plan_action", "scalar"),
    "pac_record_effectiveness_review": RouteContract("quality_action_plan", "scalar"),
    "pac_submit_effectiveness_review": RouteContract("quality_action_plan", "scalar"),
    "pac_approve_effectiveness_review": RouteContract("quality_action_plan", "scalar"),
    "pac_reject_effectiveness_review": RouteContract("quality_action_plan", "scalar"),
    "pac_reopen_action_plan": RouteContract("quality_action_plan", "scalar"),
    "pac_promote_solution_pattern": RouteContract("quality_solution_pattern", "scalar"),
    "pac_dispatch_notifications": RouteContract("quality_action_plan_notifications", "scalar"),
    "pac_upsert_rnc_8d": RouteContract("quality_action_plan_rnc_8d", "scalar"),
    "pac_export_rnc_8d": RouteContract("quality_action_plan_rnc_8d", "scalar"),
    "pac_list_plan_evidences": RouteContract("quality_action_plan_evidence", "paged_list"),
    "pac_attach_plan_evidence": RouteContract("quality_action_plan_evidence", "scalar"),
    "pac_delete_plan_evidence": RouteContract("quality_action_plan_evidence", "scalar"),
    "pac_search_similar_cases": RouteContract("pac_quality_similar_cases", "paged_list"),
    "pac_search_solution_patterns": RouteContract("pac_quality_solution_patterns", "paged_list"),
    "pac_suggest_actions": RouteContract("pac_quality_action_suggestions", "composite_analysis"),
}


def default_entity(operation_id: str) -> str:
    token = str(operation_id or "").strip().lower()
    return token or "pac_quality"


def resolve_contract(
    operation_id: str,
    *,
    entity: str | None = None,
    shape: str | None = None,
) -> tuple[str, str]:
    contract = ROUTE_CONTRACTS.get(str(operation_id or "").strip())
    resolved_entity = entity or (contract.entity if contract else default_entity(operation_id))
    resolved_shape = shape or (contract.shape if contract else "scalar")
    return resolved_entity, resolved_shape
