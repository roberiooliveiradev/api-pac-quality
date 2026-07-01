from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Body, File, Form, Query, UploadFile
from pydantic import BaseModel, Field, field_validator, model_validator

from app.domain.services.ishikawa_causes_service import (
    ISHIKAWA_CATEGORY_FIELDS,
    normalize_category_causes,
)
from app.domain.services.pac_quality_datetime_service import validate_optional_iso_datetime
from app.core.responses import error_response, success_response
from app.infrastructure.gateways.core_api_directory_gateway import (
    CoreApiDirectoryGateway,
    CoreApiDirectoryGatewayError,
)
from app.interface.http.delegation.pac_delpi_route_delegate import (
    delegate_binary,
    delegate_json,
    delegate_multipart,
)
from app.interface.http.schemas.quality_action_plan_openapi import Rnc8dTemplatePayloadHeader

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quality/action-plans", tags=["PAC Qualidade — planos de ação"])


def _query_params(**kwargs: Any) -> dict[str, Any]:
    return {key: value for key, value in kwargs.items() if value is not None}


class _PlanTimestampValidationMixin(BaseModel):
    detected_at: str | None = None
    reported_at: str | None = None

    @field_validator("detected_at", "reported_at", mode="before")
    @classmethod
    def _validate_plan_timestamps(cls, value: object, info) -> str | None:
        field_name = str(getattr(info, "field_name", "data/hora"))
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError(f"{field_name} deve ser texto em formato ISO 8601.")
        return validate_optional_iso_datetime(value, field_name=field_name)


class CreateActionPlanBody(_PlanTimestampValidationMixin):
    title: str = Field(..., min_length=2, max_length=500)
    customer_name: str | None = Field(default=None, max_length=300)
    customer_code: str | None = Field(default=None, max_length=20)
    customer_store: str | None = Field(default=None, max_length=10)
    customer_contact: str | None = Field(default=None, max_length=300)
    customer_contact_email: str | None = Field(default=None, max_length=300)
    customer_contact_phone: str | None = Field(default=None, max_length=100)
    delpi_contact_name: str | None = Field(default=None, max_length=300)
    delpi_contact_area: str | None = Field(
        default=None,
        pattern="^(comercial|qualidade|pcp|engenharia|outro)$",
    )
    delpi_sales_rep: str | None = Field(default=None, max_length=300)
    delpi_quality_contact: str | None = Field(default=None, max_length=300)
    source_type: str | None = Field(
        default=None,
        pattern="^(email|message|spreadsheet|pdf|image|manual_text|system_reference|other)$",
    )
    source_reference: str | None = Field(default=None, max_length=500)
    product_code: str | None = Field(default=None, max_length=50)
    product_description: str | None = Field(default=None, max_length=500)
    batch_number: str | None = Field(default=None, max_length=100)
    reported_problem: str | None = None
    severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    status: str = Field(default="triage", pattern="^(draft|triage)$")
    owner_user_id: str | None = Field(default=None, max_length=100)
    branch_code: str = Field(..., pattern="^(01|02)$")
    nonconformity_scope: str = Field(
        default="external",
        pattern="^(internal|external)$",
    )
    department: str | None = Field(default=None, max_length=200)
    problem_category: str | None = Field(default=None, max_length=200)
    symptom_tags: list[str] | None = None
    root_cause_category: str | None = Field(default=None, max_length=200)
    failure_mode: str | None = Field(default=None, max_length=300)
    recurrence_key: str | None = Field(default=None, max_length=500)
    customer_template: str | None = Field(
        default=None,
        pattern="^(generic|rnc_8d)$",
    )
    client_nc_registry: str | None = Field(default=None, max_length=100)
    export_template_key: str | None = Field(
        default=None,
        max_length=50,
        description="Template Excel 8D preferido (ex.: weg_wfr20997, delpi_8d).",
    )


class UpdateActionPlanBody(_PlanTimestampValidationMixin):
    title: str | None = Field(default=None, min_length=2, max_length=500)
    customer_name: str | None = Field(default=None, max_length=300)
    customer_code: str | None = Field(default=None, max_length=20)
    customer_store: str | None = Field(default=None, max_length=10)
    customer_contact: str | None = Field(default=None, max_length=300)
    customer_contact_email: str | None = Field(default=None, max_length=300)
    customer_contact_phone: str | None = Field(default=None, max_length=100)
    delpi_contact_name: str | None = Field(default=None, max_length=300)
    delpi_contact_area: str | None = Field(
        default=None,
        pattern="^(comercial|qualidade|pcp|engenharia|outro)$",
    )
    delpi_sales_rep: str | None = Field(default=None, max_length=300)
    delpi_quality_contact: str | None = Field(default=None, max_length=300)
    source_type: str | None = Field(
        default=None,
        pattern="^(email|message|spreadsheet|pdf|image|manual_text|system_reference|other)$",
    )
    source_reference: str | None = Field(default=None, max_length=500)
    product_code: str | None = Field(default=None, max_length=50)
    product_description: str | None = Field(default=None, max_length=500)
    batch_number: str | None = Field(default=None, max_length=100)
    reported_problem: str | None = None
    severity: str | None = Field(default=None, pattern="^(low|medium|high|critical)$")
    owner_user_id: str | None = Field(default=None, max_length=100)
    branch_code: str | None = Field(default=None, pattern="^(01|02)$")
    nonconformity_scope: str | None = Field(default=None, pattern="^(internal|external)$")
    department: str | None = Field(default=None, max_length=200)
    problem_category: str | None = Field(default=None, max_length=200)
    symptom_tags: list[str] | None = None
    root_cause_category: str | None = Field(default=None, max_length=200)
    failure_mode: str | None = Field(default=None, max_length=300)
    recurrence_key: str | None = Field(default=None, max_length=500)
    customer_template: str | None = Field(
        default=None,
        pattern="^(generic|rnc_8d)$",
    )
    client_nc_registry: str | None = Field(default=None, max_length=100)
    export_template_key: str | None = Field(
        default=None,
        max_length=50,
        description="Template Excel 8D preferido (ex.: weg_wfr20997, delpi_8d).",
    )


class UpdateActionPlanStatusBody(BaseModel):
    status: str = Field(
        ...,
        pattern=(
            "^(draft|triage|containment|root_cause_analysis|action_plan_defined|"
            "in_progress|waiting_validation|completed|cancelled)$"
        ),
    )
    comment: str | None = None


class IshikawaBody(BaseModel):
    machine: list[str] | None = None
    method_process: list[str] | None = None
    material: list[str] | None = None
    manpower: list[str] | None = None
    measurement: list[str] | None = None
    environment: list[str] | None = None
    notes: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_categories(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        normalized = dict(data)
        for key in ISHIKAWA_CATEGORY_FIELDS:
            if key in normalized:
                normalized[key] = normalize_category_causes(normalized.get(key))
        return normalized


class FiveWhyStepBody(BaseModel):
    question: str = ""
    answer: str = ""


class FiveWhysBody(BaseModel):
    occurrence_whys: list[str | FiveWhyStepBody] | None = None
    detection_whys: list[str | FiveWhyStepBody] | None = None
    root_cause: str | None = None
    confidence_level: str | None = Field(default=None, pattern="^(low|medium|high)$")
    why_1: str | None = None
    why_2: str | None = None
    why_3: str | None = None
    why_4: str | None = None
    why_5: str | None = None
    detection_why_1: str | None = None
    detection_why_2: str | None = None
    detection_why_3: str | None = None
    detection_why_4: str | None = None
    detection_why_5: str | None = None


class ActionResponsibleBody(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=200)
    user_id: str | None = Field(default=None, max_length=100)


class ActionItemBody(BaseModel):
    action_type: str = Field(
        ...,
        pattern="^(containment|corrective|preventive|verification|standardization|training)$",
    )
    description: str = Field(..., min_length=3)
    responsible_user_id: str | None = None
    responsible_name: str | None = None
    responsibles: list[ActionResponsibleBody] | None = None
    department: str | None = None
    due_date: str | None = None
    status: str = Field(default="pending", pattern="^(pending|in_progress|blocked)$")
    evidence_required: bool = False
    cause_track: str | None = Field(default=None, pattern="^(occurrence|detection)$")


class CreateActionsBody(BaseModel):
    actions: list[ActionItemBody] = Field(..., min_length=1)


class UpdateActionBody(BaseModel):
    action_type: str | None = Field(
        default=None,
        pattern="^(containment|corrective|preventive|verification|standardization|training)$",
    )
    description: str | None = Field(default=None, min_length=3)
    responsible_user_id: str | None = None
    responsible_name: str | None = None
    responsibles: list[ActionResponsibleBody] | None = None
    department: str | None = None
    due_date: str | None = None
    status: str | None = Field(
        default=None,
        pattern="^(pending|in_progress|blocked|completed|cancelled|overdue)$",
    )
    evidence_required: bool | None = None
    cause_track: str | None = Field(default=None, pattern="^(occurrence|detection)$")


class UpdateEvidenceBody(BaseModel):
    evidence_type: str | None = Field(
        default=None,
        pattern="^(email|message|spreadsheet|pdf|image|manual_text|system_reference|other)$",
    )
    section: str | None = Field(
        default=None,
        pattern=(
            "^(general|nc_description|containment|root_cause|corrective|"
            "effectiveness|preventive|documentation|attachments)$"
        ),
    )
    description: str | None = None
    action_id: str | None = None
    knowledge_visible: bool | None = None


class TeamMemberBody(BaseModel):
    member_name: str = Field(..., min_length=1, max_length=200)
    member_user_id: str | None = Field(default=None, max_length=100)
    department: str | None = Field(default=None, max_length=200)
    is_leader: bool = False
    sort_order: int = 0


class Rnc8dReportBody(BaseModel):
    client_nc_registry: str | None = Field(default=None, max_length=100)
    customer_name: str | None = Field(default=None, max_length=300)
    customer_contact: str | None = Field(default=None, max_length=300)
    customer_contact_email: str | None = Field(default=None, max_length=300)
    customer_contact_phone: str | None = Field(default=None, max_length=100)
    delpi_contact_name: str | None = Field(default=None, max_length=300)
    delpi_contact_area: str | None = Field(
        default=None,
        pattern="^(comercial|qualidade|pcp|engenharia|outro)$",
    )
    delpi_sales_rep: str | None = Field(default=None, max_length=300)
    delpi_quality_contact: str | None = Field(default=None, max_length=300)
    product_code: str | None = Field(default=None, max_length=50)
    product_description: str | None = Field(default=None, max_length=500)
    batch_number: str | None = Field(default=None, max_length=100)
    reported_problem: str | None = None
    template_payload: Rnc8dTemplatePayloadHeader | None = Field(
        default=None,
        description="Seções 8D; cabeçalho material/NF — ver Rnc8dTemplatePayloadHeader no OpenAPI.",
    )
    team_members: list[TeamMemberBody] | None = None


class EffectivenessReviewBody(BaseModel):
    effectiveness_status: str = Field(
        ...,
        pattern="^(pending|effective|partially_effective|ineffective|not_verified)$",
    )
    notes: str | None = None


class SubmitEffectivenessReviewBody(BaseModel):
    effectiveness_status: str = Field(
        ...,
        pattern="^(effective|partially_effective|ineffective)$",
    )
    notes: str | None = None


class ReopenActionPlanBody(BaseModel):
    reason: str = Field(..., min_length=5)
    target_status: str | None = Field(
        default=None,
        pattern=(
            "^(triage|containment|root_cause_analysis|action_plan_defined|"
            "in_progress|waiting_validation)$"
        ),
    )


@router.get("/export-templates", operation_id="pac_list_export_templates")
def list_rnc_8d_export_templates():
    return delegate_json(
        method="GET",
        path_suffix="/export-templates",
        pac_operation_id="pac_list_export_templates",
    )


@router.get("/assignable-users", operation_id="pac_search_assignable_users")
def search_assignable_users(
    q: str = Query(..., min_length=2, description="Nome ou e-mail (mín. 2 caracteres)."),
    limit: int = Query(default=10, ge=1, le=20),
):
    try:
        items = CoreApiDirectoryGateway().search_assignable_users(query=q, limit=limit)
        return success_response({"items": items})
    except CoreApiDirectoryGatewayError as exc:
        return error_response(str(exc), status_code=503, code="CORE_API_UNAVAILABLE")
    except Exception:
        logger.exception("Erro ao buscar usuários atribuíveis PAC.")
        return error_response("Erro ao buscar usuários.", status_code=500)


@router.post("", operation_id="pac_create_action_plan")
def create_action_plan(body: CreateActionPlanBody = Body(...)):
    return delegate_json(
        method="POST",
        path_suffix="",
        pac_operation_id="pac_create_action_plan",
        json_body=body.model_dump(exclude_unset=True),
    )


@router.get("", operation_id="pac_list_action_plans")
def list_action_plans(
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None, pattern="^(low|medium|high|critical)$"),
    product_code: str | None = Query(default=None),
    customer_name: str | None = Query(default=None),
    owner_user_id: str | None = Query(default=None),
    branch_code: str | None = Query(default=None, pattern="^(01|02)$"),
    nonconformity_scope: str | None = Query(default=None, pattern="^(internal|external)$"),
    code: str | None = Query(default=None, description="Código do plano (ex.: PAC-2026-0029)."),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    return delegate_json(
        method="GET",
        path_suffix="",
        pac_operation_id="pac_list_action_plans",
        query=_query_params(
            status=status,
            severity=severity,
            product_code=product_code,
            customer_name=customer_name,
            owner_user_id=owner_user_id,
            branch_code=branch_code,
            nonconformity_scope=nonconformity_scope,
            code=code,
            page=page,
            page_size=page_size,
        ),
    )


@router.get("/{plan_id}", operation_id="pac_get_action_plan")
def get_action_plan(plan_id: str, detail: bool = Query(default=True)):
    return delegate_json(
        method="GET",
        path_suffix=f"/{plan_id}",
        pac_operation_id="pac_get_action_plan",
        query={"detail": detail},
    )


@router.put("/{plan_id}/ishikawa", operation_id="pac_upsert_ishikawa")
def upsert_ishikawa(plan_id: str, body: IshikawaBody = Body(...)):
    return delegate_json(
        method="PUT",
        path_suffix=f"/{plan_id}/ishikawa",
        pac_operation_id="pac_upsert_ishikawa",
        json_body=body.model_dump(exclude_unset=True),
    )


@router.put("/{plan_id}/five-whys", operation_id="pac_upsert_five_whys")
def upsert_five_whys(plan_id: str, body: FiveWhysBody = Body(...)):
    return delegate_json(
        method="PUT",
        path_suffix=f"/{plan_id}/five-whys",
        pac_operation_id="pac_upsert_five_whys",
        json_body=body.model_dump(exclude_unset=True),
    )


@router.post("/{plan_id}/actions", operation_id="pac_create_plan_actions")
def create_plan_actions(plan_id: str, body: CreateActionsBody = Body(...)):
    return delegate_json(
        method="POST",
        path_suffix=f"/{plan_id}/actions",
        pac_operation_id="pac_create_plan_actions",
        json_body=body.model_dump(exclude_unset=True),
    )


@router.patch("/{plan_id}/actions/{action_id}", operation_id="pac_update_plan_action")
def update_plan_action(plan_id: str, action_id: str, body: UpdateActionBody = Body(...)):
    return delegate_json(
        method="PATCH",
        path_suffix=f"/{plan_id}/actions/{action_id}",
        pac_operation_id="pac_update_plan_action",
        json_body=body.model_dump(exclude_unset=True),
    )


@router.delete("/{plan_id}/actions/{action_id}", operation_id="pac_delete_plan_action")
def delete_plan_action(plan_id: str, action_id: str):
    return delegate_json(
        method="DELETE",
        path_suffix=f"/{plan_id}/actions/{action_id}",
        pac_operation_id="pac_delete_plan_action",
    )


@router.post("/{plan_id}/effectiveness-review", operation_id="pac_record_effectiveness_review")
def record_effectiveness_review(plan_id: str, body: EffectivenessReviewBody = Body(...)):
    return delegate_json(
        method="POST",
        path_suffix=f"/{plan_id}/effectiveness-review",
        pac_operation_id="pac_record_effectiveness_review",
        json_body=body.model_dump(exclude_unset=True),
    )


@router.post(
    "/{plan_id}/effectiveness-review/submit",
    operation_id="pac_submit_effectiveness_review",
)
def submit_effectiveness_review(plan_id: str, body: SubmitEffectivenessReviewBody = Body(...)):
    return delegate_json(
        method="POST",
        path_suffix=f"/{plan_id}/effectiveness-review/submit",
        pac_operation_id="pac_submit_effectiveness_review",
        json_body=body.model_dump(exclude_unset=True),
    )


@router.patch("/{plan_id}", operation_id="pac_update_action_plan")
def update_action_plan(plan_id: str, body: UpdateActionPlanBody = Body(...)):
    return delegate_json(
        method="PATCH",
        path_suffix=f"/{plan_id}",
        pac_operation_id="pac_update_action_plan",
        json_body=body.model_dump(exclude_unset=True),
    )


@router.delete("/{plan_id}", operation_id="pac_delete_action_plan")
def delete_action_plan(plan_id: str):
    return delegate_json(
        method="DELETE",
        path_suffix=f"/{plan_id}",
        pac_operation_id="pac_delete_action_plan",
    )


@router.patch("/{plan_id}/status", operation_id="pac_update_action_plan_status")
def update_action_plan_status(plan_id: str, body: UpdateActionPlanStatusBody = Body(...)):
    return delegate_json(
        method="PATCH",
        path_suffix=f"/{plan_id}/status",
        pac_operation_id="pac_update_action_plan_status",
        json_body=body.model_dump(exclude_unset=True),
    )


@router.post("/{plan_id}/reopen", operation_id="pac_reopen_action_plan")
def reopen_action_plan(plan_id: str, body: ReopenActionPlanBody = Body(...)):
    return delegate_json(
        method="POST",
        path_suffix=f"/{plan_id}/reopen",
        pac_operation_id="pac_reopen_action_plan",
        json_body=body.model_dump(exclude_unset=True),
    )


@router.get("/{plan_id}/revisions", operation_id="pac_list_plan_revisions")
def list_plan_revisions(
    plan_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    return delegate_json(
        method="GET",
        path_suffix=f"/{plan_id}/revisions",
        pac_operation_id="pac_list_plan_revisions",
        query=_query_params(page=page, page_size=page_size),
    )


@router.get(
    "/{plan_id}/revisions/{revision_number}",
    operation_id="pac_get_plan_revision",
)
def get_plan_revision(plan_id: str, revision_number: int):
    return delegate_json(
        method="GET",
        path_suffix=f"/{plan_id}/revisions/{revision_number}",
        pac_operation_id="pac_get_plan_revision",
    )


@router.post(
    "/{plan_id}/revisions/{revision_number}/restore",
    operation_id="pac_restore_plan_revision",
)
def restore_plan_revision(plan_id: str, revision_number: int):
    return delegate_json(
        method="POST",
        path_suffix=f"/{plan_id}/revisions/{revision_number}/restore",
        pac_operation_id="pac_restore_plan_revision",
    )


@router.put("/{plan_id}/rnc-8d", operation_id="pac_upsert_rnc_8d")
def upsert_rnc_8d_report(plan_id: str, body: Rnc8dReportBody = Body(...)):
    return delegate_json(
        method="PUT",
        path_suffix=f"/{plan_id}/rnc-8d",
        pac_operation_id="pac_upsert_rnc_8d",
        json_body=body.model_dump(exclude_unset=True),
    )


@router.get("/{plan_id}/export/rnc-8d", operation_id="pac_export_rnc_8d")
def export_rnc_8d_spreadsheet(
    plan_id: str,
    template_key: str | None = Query(
        default=None,
        description="Template Excel 8D (weg_wfr20997, delpi_8d). Omitir para inferir pelo plano/cliente.",
    ),
):
    return delegate_binary(
        method="GET",
        path_suffix=f"/{plan_id}/export/rnc-8d",
        pac_operation_id="pac_export_rnc_8d",
        query=_query_params(template_key=template_key),
    )


@router.get("/{plan_id}/evidences", operation_id="pac_list_plan_evidences")
def list_plan_evidences(plan_id: str):
    return delegate_json(
        method="GET",
        path_suffix=f"/{plan_id}/evidences",
        pac_operation_id="pac_list_plan_evidences",
    )


@router.post("/{plan_id}/evidences", operation_id="pac_attach_plan_evidence")
async def upload_plan_evidence(
    plan_id: str,
    evidence_type: str = Form(
        ...,
        pattern="^(email|message|spreadsheet|pdf|image|manual_text|system_reference|other)$",
    ),
    section: str = Form(
        default="general",
        pattern=(
            "^(general|nc_description|containment|root_cause|corrective|"
            "effectiveness|preventive|documentation|attachments)$"
        ),
    ),
    description: str | None = Form(default=None),
    knowledge_visible: bool = Form(default=True),
    action_id: str | None = Form(default=None),
    file: UploadFile = File(...),
):
    content = await file.read()
    form_data: dict[str, str] = {
        "evidence_type": evidence_type,
        "section": section,
        "knowledge_visible": str(knowledge_visible).lower(),
    }
    if description:
        form_data["description"] = description
    if action_id:
        form_data["action_id"] = action_id
    return delegate_multipart(
        path_suffix=f"/{plan_id}/evidences",
        pac_operation_id="pac_attach_plan_evidence",
        form_data=form_data,
        file_field="file",
        file_name=file.filename or "evidence.bin",
        file_content=content,
        file_content_type=file.content_type,
    )


@router.get(
    "/{plan_id}/evidences/{evidence_id}/file",
    operation_id="pac_download_plan_evidence",
    responses={
        200: {
            "description": "Arquivo binário da evidência",
            "content": {
                "application/octet-stream": {"schema": {"type": "string", "format": "binary"}},
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {
                    "schema": {"type": "string", "format": "binary"}
                },
                "application/pdf": {"schema": {"type": "string", "format": "binary"}},
            },
        }
    },
)
def download_plan_evidence(plan_id: str, evidence_id: str):
    return delegate_binary(
        method="GET",
        path_suffix=f"/{plan_id}/evidences/{evidence_id}/file",
        pac_operation_id="pac_download_plan_evidence",
    )


@router.get(
    "/{plan_id}/evidences/{evidence_id}/content",
    operation_id="pac_get_plan_evidence_content",
)
def get_plan_evidence_content(plan_id: str, evidence_id: str):
    return delegate_json(
        method="GET",
        path_suffix=f"/{plan_id}/evidences/{evidence_id}/content",
        pac_operation_id="pac_get_plan_evidence_content",
    )


@router.patch(
    "/{plan_id}/evidences/{evidence_id}",
    operation_id="pac_update_plan_evidence",
)
def update_plan_evidence(
    plan_id: str,
    evidence_id: str,
    body: UpdateEvidenceBody = Body(...),
):
    return delegate_json(
        method="PATCH",
        path_suffix=f"/{plan_id}/evidences/{evidence_id}",
        pac_operation_id="pac_update_plan_evidence",
        json_body=body.model_dump(exclude_unset=True),
    )


@router.delete("/{plan_id}/evidences/{evidence_id}", operation_id="pac_delete_plan_evidence")
def delete_plan_evidence(plan_id: str, evidence_id: str):
    return delegate_json(
        method="DELETE",
        path_suffix=f"/{plan_id}/evidences/{evidence_id}",
        pac_operation_id="pac_delete_plan_evidence",
    )
