"""Mapeamento operationId api-delpi → pac_* (contrato GPT)."""

from __future__ import annotations

# Transacional + leituras do analista (paridade com test_pac_delpi_*_parity.py).
DELPI_TO_PAC_OPERATION_ID: dict[str, str] = {
    "list_quality_action_plans": "pac_list_action_plans",
    "get_quality_action_plan_detail": "pac_get_action_plan",
    "list_quality_action_plan_evidences": "pac_list_plan_evidences",
    "list_quality_action_plan_export_templates": "pac_list_export_templates",
    "export_quality_action_plan_rnc_8d": "pac_export_rnc_8d",
    "create_quality_action_plan": "pac_create_action_plan",
    "update_quality_action_plan": "pac_update_action_plan",
    "delete_quality_action_plan": "pac_delete_action_plan",
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
    "attach_quality_action_plan_evidence": "pac_attach_plan_evidence",
    "update_quality_action_plan_evidence": "pac_update_plan_evidence",
    "get_quality_action_plan_evidence_content": "pac_get_plan_evidence_content",
    "delete_quality_action_plan_evidence": "pac_delete_plan_evidence",
    "list_quality_action_plan_revisions": "pac_list_plan_revisions",
    "get_quality_action_plan_revision": "pac_get_plan_revision",
    "restore_quality_action_plan_revision": "pac_restore_plan_revision",
    # Inteligência com paridade de path (opcional na delegação).
    "assess_quality_action_plan_recurrence_on_opening": "pac_assess_recurrence_on_opening",
    "suggest_quality_action_plan_evidence_tags": "pac_suggest_evidence_tags",
    "suggest_quality_action_plan_evidence_tags_from_image": "pac_suggest_evidence_tags_from_image",
}

PAC_TRANSACTIONAL_PREFIX = "/quality/action-plans"
