from __future__ import annotations

from datetime import datetime
from typing import Any


PLAN_SELECT = """
    SELECT p.id,
           p.code,
           p.title,
           p.customer_name,
           p.customer_contact,
           p.nonconformity_scope,
           p.customer_template,
           p.client_nc_registry,
           p.template_payload,
           p.source_type,
           p.source_reference,
           p.product_code,
           p.product_description,
           p.batch_number,
           p.reported_problem,
           p.detected_at,
           p.reported_at,
           p.severity,
           p.status,
           p.created_by_user_id,
           p.owner_user_id,
           p.branch_code,
           p.department,
           p.problem_category,
           p.symptom_tags,
           p.root_cause_category,
           p.failure_mode,
           p.effectiveness_status,
           p.effectiveness_verified_at,
           p.effectiveness_notes,
           p.effectiveness_approval_status,
           p.effectiveness_proposed_status,
           p.effectiveness_submitted_at,
           p.effectiveness_submitted_by,
           p.effectiveness_reviewed_at,
           p.effectiveness_reviewed_by,
           p.effectiveness_rejection_reason,
           p.recurrence_key,
           p.created_at,
           p.updated_at,
           p.closed_at
      FROM quality.quality_action_plans p
"""


class QualityActionPlanRepositoryPort:
    def next_plan_code(self) -> str: ...

    def create_plan(self, fields: dict[str, Any]) -> dict[str, Any]: ...

    def get_plan_by_id(self, plan_id: str) -> dict[str, Any] | None: ...

    def get_plan_detail(self, plan_id: str) -> dict[str, Any] | None: ...

    def list_plans(
        self,
        *,
        status: str | None = None,
        severity: str | None = None,
        product_code: str | None = None,
        customer_name: str | None = None,
        owner_user_id: str | None = None,
        branch_code: str | None = None,
        nonconformity_scope: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]: ...

    def update_plan(self, plan_id: str, fields: dict[str, Any]) -> dict[str, Any] | None: ...

    def update_plan_status(
        self,
        plan_id: str,
        *,
        status: str,
        updated_by: str,
        comment: str | None = None,
    ) -> dict[str, Any] | None: ...

    def append_history(
        self,
        *,
        plan_id: str,
        event_type: str,
        created_by: str,
        old_value: str | None = None,
        new_value: str | None = None,
        comment: str | None = None,
    ) -> None: ...

    def upsert_ishikawa(
        self, plan_id: str, fields: dict[str, Any], *, updated_by: str
    ) -> dict[str, Any] | None: ...

    def get_ishikawa(self, plan_id: str) -> dict[str, Any] | None: ...

    def upsert_five_whys(
        self, plan_id: str, fields: dict[str, Any], *, updated_by: str
    ) -> dict[str, Any] | None: ...

    def get_five_whys(self, plan_id: str) -> dict[str, Any] | None: ...

    def create_actions(
        self, plan_id: str, actions: list[dict[str, Any]], *, created_by: str
    ) -> list[dict[str, Any]] | None: ...

    def list_actions(self, plan_id: str) -> list[dict[str, Any]]: ...

    def update_action(
        self, plan_id: str, action_id: str, fields: dict[str, Any], *, updated_by: str
    ) -> dict[str, Any] | None: ...

    def record_effectiveness_review(
        self, plan_id: str, fields: dict[str, Any], *, updated_by: str
    ) -> dict[str, Any] | None: ...

    def submit_effectiveness_review(
        self, plan_id: str, fields: dict[str, Any], *, updated_by: str
    ) -> dict[str, Any] | None: ...

    def approve_effectiveness_review(
        self, plan_id: str, *, updated_by: str
    ) -> dict[str, Any] | None: ...

    def reject_effectiveness_review(
        self, plan_id: str, *, reason: str, updated_by: str
    ) -> dict[str, Any] | None: ...

    def reopen_plan(
        self,
        plan_id: str,
        *,
        target_status: str,
        reason: str,
        updated_by: str,
    ) -> dict[str, Any] | None: ...

    def append_audit_log(
        self,
        *,
        entity_type: str,
        entity_id: str,
        event_type: str,
        actor_user_id: str,
        payload: dict[str, Any] | None = None,
        auto_commit: bool = True,
    ) -> None: ...

    def list_actions_due_within_days(self, *, days_ahead: int = 2) -> list[dict[str, Any]]: ...

    def list_stalled_critical_plans(self, *, stall_days: int = 5) -> list[dict[str, Any]]: ...

    def notification_already_sent(self, notification_key: str) -> bool: ...

    def record_notification_dispatch(
        self,
        *,
        notification_key: str,
        event_type: str,
        recipient_user_id: str | None,
        entity_type: str | None,
        entity_id: str | None,
    ) -> None: ...

    def list_history(self, plan_id: str, *, limit: int = 100) -> list[dict[str, Any]]: ...

    def get_dashboard_summary(
        self,
        *,
        branch_code: str | None = None,
        nonconformity_scope: str | None = None,
    ) -> dict[str, Any]: ...

    def upsert_rnc_8d_report(
        self, plan_id: str, fields: dict[str, Any], *, updated_by: str
    ) -> dict[str, Any] | None: ...

    def list_evidences(self, plan_id: str) -> list[dict[str, Any]]: ...

    def get_evidence(self, plan_id: str, evidence_id: str) -> dict[str, Any] | None: ...

    def create_evidence(self, plan_id: str, fields: dict[str, Any]) -> dict[str, Any] | None: ...

    def delete_evidence(self, plan_id: str, evidence_id: str) -> dict[str, Any] | None: ...


def serialize_row(row: dict[str, Any] | None, *, id_keys: tuple[str, ...] = ("id",)) -> dict[str, Any] | None:
    if row is None:
        return None
    result = dict(row)
    for key in id_keys:
        if result.get(key) is not None:
            result[key] = str(result[key])
    for key, value in list(result.items()):
        if isinstance(value, datetime):
            result[key] = value.isoformat()
    return result


def serialize_plan_row(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    for key in ("id",):
        if result.get(key) is not None:
            result[key] = str(result[key])
    for key in (
        "detected_at",
        "reported_at",
        "effectiveness_verified_at",
        "effectiveness_submitted_at",
        "effectiveness_reviewed_at",
        "created_at",
        "updated_at",
        "closed_at",
    ):
        value = result.get(key)
        if isinstance(value, datetime):
            result[key] = value.isoformat()
    tags = result.get("symptom_tags")
    if tags is None:
        result["symptom_tags"] = []
    if result.get("template_payload") is None:
        result["template_payload"] = {}
    return result
