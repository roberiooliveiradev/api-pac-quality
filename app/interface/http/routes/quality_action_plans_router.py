from __future__ import annotations

import logging

from fastapi import APIRouter, Body, File, Form, Query, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field, model_validator

from app.domain.services.ishikawa_causes_service import (
    ISHIKAWA_CATEGORY_FIELDS,
    normalize_category_causes,
)

from app.interface.http.middleware.pac_request_context import get_pac_authenticated_user_id
from app.application.services.pac_evidence_storage import (
    PacEvidenceStorage,
    PacEvidenceStorageError,
)
from app.composition.quality_action_plans_composer import (
    build_create_plan_actions_use_case,
    build_create_quality_action_plan_use_case,
    build_delete_plan_action_use_case,
    build_get_plan_detail_use_case,
    build_get_quality_action_plan_use_case,
    build_list_quality_action_plans_use_case,
    build_quality_action_plan_repository,
    build_record_effectiveness_review_use_case,
    build_reopen_quality_action_plan_use_case,
    build_submit_effectiveness_review_use_case,
    build_update_plan_action_use_case,
    build_update_quality_action_plan_status_use_case,
    build_update_quality_action_plan_use_case,
    build_upsert_five_whys_use_case,
    build_upsert_ishikawa_use_case,
)
from app.application.use_cases.quality_action_plans_use_cases import (
    CreateQualityActionPlanRequest,
    UpdateQualityActionPlanRequest,
)
from app.application.use_cases.quality_action_plan_analysis_use_cases import (
    CreateActionItemRequest,
    EffectivenessReviewRequest,
    UpsertFiveWhysRequest,
    UpsertIshikawaRequest,
)
from app.core.responses import error_response, not_found_response, success_response
from app.domain.services.rnc_8d_excel_export_service import (
    build_rnc_8d_workbook,
    collect_image_annexes_for_export,
)
from app.infrastructure.persistence.plugins.plugin_base_repository import PluginsRepositoryError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quality/action-plans", tags=["PAC Qualidade — planos de ação"])


class CreateActionPlanBody(BaseModel):
    title: str = Field(..., min_length=2, max_length=500)
    customer_name: str | None = Field(default=None, max_length=300)
    customer_contact: str | None = Field(default=None, max_length=300)
    source_type: str | None = Field(
        default=None,
        pattern="^(email|message|spreadsheet|pdf|image|manual_text|system_reference|other)$",
    )
    source_reference: str | None = Field(default=None, max_length=500)
    product_code: str | None = Field(default=None, max_length=50)
    product_description: str | None = Field(default=None, max_length=500)
    batch_number: str | None = Field(default=None, max_length=100)
    reported_problem: str | None = None
    detected_at: str | None = None
    reported_at: str | None = None
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


class UpdateActionPlanBody(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=500)
    customer_name: str | None = Field(default=None, max_length=300)
    customer_contact: str | None = Field(default=None, max_length=300)
    source_type: str | None = Field(
        default=None,
        pattern="^(email|message|spreadsheet|pdf|image|manual_text|system_reference|other)$",
    )
    source_reference: str | None = Field(default=None, max_length=500)
    product_code: str | None = Field(default=None, max_length=50)
    product_description: str | None = Field(default=None, max_length=500)
    batch_number: str | None = Field(default=None, max_length=100)
    reported_problem: str | None = None
    detected_at: str | None = None
    reported_at: str | None = None
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


class FiveWhysBody(BaseModel):
    occurrence_whys: list[str] | None = None
    detection_whys: list[str] | None = None
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


class ActionItemBody(BaseModel):
    action_type: str = Field(
        ...,
        pattern="^(containment|corrective|preventive|verification|standardization|training)$",
    )
    description: str = Field(..., min_length=3)
    responsible_user_id: str | None = None
    responsible_name: str | None = None
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
    department: str | None = None
    due_date: str | None = None
    status: str | None = Field(
        default=None,
        pattern="^(pending|in_progress|blocked|completed|cancelled|overdue)$",
    )
    evidence_required: bool | None = None
    cause_track: str | None = Field(default=None, pattern="^(occurrence|detection)$")


class TeamMemberBody(BaseModel):
    member_name: str = Field(..., min_length=1, max_length=200)
    department: str | None = Field(default=None, max_length=200)
    is_leader: bool = False
    sort_order: int = 0


class Rnc8dReportBody(BaseModel):
    client_nc_registry: str | None = Field(default=None, max_length=100)
    customer_name: str | None = Field(default=None, max_length=300)
    customer_contact: str | None = Field(default=None, max_length=300)
    product_code: str | None = Field(default=None, max_length=50)
    product_description: str | None = Field(default=None, max_length=500)
    batch_number: str | None = Field(default=None, max_length=100)
    reported_problem: str | None = None
    template_payload: dict | None = None
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


def _current_user_id() -> str:
    return get_pac_authenticated_user_id()


@router.post("", operation_id="pac_create_action_plan")
def create_action_plan(body: CreateActionPlanBody = Body(...)):
    try:
        use_case = build_create_quality_action_plan_use_case()
        plan = use_case.execute(
            CreateQualityActionPlanRequest(
                title=body.title,
                created_by_user_id=_current_user_id(),
                customer_name=body.customer_name,
                customer_contact=body.customer_contact,
                source_type=body.source_type,
                source_reference=body.source_reference,
                product_code=body.product_code,
                product_description=body.product_description,
                batch_number=body.batch_number,
                reported_problem=body.reported_problem,
                detected_at=body.detected_at,
                reported_at=body.reported_at,
                severity=body.severity,
                status=body.status,
                owner_user_id=body.owner_user_id,
                branch_code=body.branch_code,
                nonconformity_scope=body.nonconformity_scope,
                department=body.department,
                problem_category=body.problem_category,
                symptom_tags=body.symptom_tags,
                root_cause_category=body.root_cause_category,
                failure_mode=body.failure_mode,
                recurrence_key=body.recurrence_key,
            )
        )
        if body.customer_template or body.client_nc_registry:
            repo = build_quality_action_plan_repository()
            repo.update_plan(
                str(plan["id"]),
                {
                    "customer_template": body.customer_template,
                    "client_nc_registry": body.client_nc_registry,
                    "updated_by_user_id": _current_user_id(),
                },
            )
            refreshed = build_get_quality_action_plan_use_case().execute(str(plan["id"]))
            if refreshed:
                plan = refreshed
        return success_response(
            plan,
            message="Plano de ação criado com sucesso.",
        )
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except PluginsRepositoryError as exc:
        logger.exception("Erro de persistência ao criar plano PAC.")
        return error_response(str(exc), status_code=500, code="PAC_REPOSITORY_ERROR")
    except Exception:
        logger.exception("Erro inesperado ao criar plano PAC.")
        return error_response("Erro interno ao criar plano de ação.", status_code=500)


@router.get("", operation_id="pac_list_action_plans")
def list_action_plans(
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None, pattern="^(low|medium|high|critical)$"),
    product_code: str | None = Query(default=None),
    customer_name: str | None = Query(default=None),
    owner_user_id: str | None = Query(default=None),
    branch_code: str | None = Query(default=None, pattern="^(01|02)$"),
    nonconformity_scope: str | None = Query(default=None, pattern="^(internal|external)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    try:
        use_case = build_list_quality_action_plans_use_case()
        result = use_case.execute(
            status=status,
            severity=severity,
            product_code=product_code,
            customer_name=customer_name,
            owner_user_id=owner_user_id,
            branch_code=branch_code,
            nonconformity_scope=nonconformity_scope,
            page=page,
            page_size=page_size,
        )
        return success_response(result)
    except PluginsRepositoryError:
        logger.exception("Erro de persistência ao listar planos PAC.")
        return error_response(
            "Erro ao consultar planos de ação.",
            status_code=500,
            code="PAC_REPOSITORY_ERROR",
        )


@router.get("/{plan_id}", operation_id="pac_get_action_plan")
def get_action_plan(plan_id: str, detail: bool = Query(default=True)):
    try:
        if detail:
            use_case = build_get_plan_detail_use_case()
            payload = use_case.execute(plan_id)
        else:
            use_case = build_get_quality_action_plan_use_case()
            plan = use_case.execute(plan_id)
            payload = {"plan": plan} if plan else None
        if not payload or not payload.get("plan"):
            return not_found_response("Plano de ação não encontrado.")
        return success_response(payload)
    except PluginsRepositoryError:
        logger.exception("Erro de persistência ao buscar plano PAC %s.", plan_id)
        return error_response(
            "Erro ao consultar plano de ação.",
            status_code=500,
            code="PAC_REPOSITORY_ERROR",
        )


@router.put("/{plan_id}/ishikawa", operation_id="pac_upsert_ishikawa")
def upsert_ishikawa(plan_id: str, body: IshikawaBody = Body(...)):
    try:
        result = build_upsert_ishikawa_use_case().execute(
            plan_id,
            UpsertIshikawaRequest(**body.model_dump()),
            updated_by=_current_user_id(),
        )
        if not result:
            return not_found_response("Plano de ação não encontrado.")
        return success_response(result, message="Análise Ishikawa registrada.")
    except PluginsRepositoryError:
        logger.exception("Erro ao salvar Ishikawa do plano %s.", plan_id)
        return error_response("Erro ao registrar Ishikawa.", status_code=500, code="PAC_REPOSITORY_ERROR")


@router.put("/{plan_id}/five-whys", operation_id="pac_upsert_five_whys")
def upsert_five_whys(plan_id: str, body: FiveWhysBody = Body(...)):
    try:
        result = build_upsert_five_whys_use_case().execute(
            plan_id,
            UpsertFiveWhysRequest(**body.model_dump()),
            updated_by=_current_user_id(),
        )
        if not result:
            return not_found_response("Plano de ação não encontrado.")
        return success_response(result, message="5 Porquês registrados.")
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except PluginsRepositoryError:
        logger.exception("Erro ao salvar 5 Porquês do plano %s.", plan_id)
        return error_response("Erro ao registrar 5 Porquês.", status_code=500, code="PAC_REPOSITORY_ERROR")


@router.post("/{plan_id}/actions", operation_id="pac_create_plan_actions")
def create_plan_actions(plan_id: str, body: CreateActionsBody = Body(...)):
    try:
        actions = [
            CreateActionItemRequest(**item.model_dump())
            for item in body.actions
        ]
        result = build_create_plan_actions_use_case().execute(
            plan_id,
            actions,
            created_by=_current_user_id(),
        )
        if result is None:
            return not_found_response("Plano de ação não encontrado.")
        return success_response({"items": result}, message="Ações registradas.")
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except PluginsRepositoryError:
        logger.exception("Erro ao criar ações do plano %s.", plan_id)
        return error_response("Erro ao registrar ações.", status_code=500, code="PAC_REPOSITORY_ERROR")


@router.patch("/{plan_id}/actions/{action_id}", operation_id="pac_update_plan_action")
def update_plan_action(plan_id: str, action_id: str, body: UpdateActionBody = Body(...)):
    try:
        fields = body.model_dump(exclude_unset=True)
        result = build_update_plan_action_use_case().execute(
            plan_id,
            action_id,
            fields,
            updated_by=_current_user_id(),
        )
        if not result:
            return not_found_response("Ação não encontrada.")
        return success_response(result, message="Ação atualizada.")
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except PluginsRepositoryError:
        logger.exception("Erro ao atualizar ação %s.", action_id)
        return error_response("Erro ao atualizar ação.", status_code=500, code="PAC_REPOSITORY_ERROR")


@router.delete("/{plan_id}/actions/{action_id}", operation_id="pac_delete_plan_action")
def delete_plan_action(plan_id: str, action_id: str):
    try:
        result = build_delete_plan_action_use_case().execute(
            plan_id,
            action_id,
            updated_by=_current_user_id(),
        )
        if not result:
            return not_found_response("Ação não encontrada.")
        return success_response(result, message="Ação removida.")
    except PluginsRepositoryError:
        logger.exception("Erro ao remover ação %s.", action_id)
        return error_response("Erro ao remover ação.", status_code=500, code="PAC_REPOSITORY_ERROR")


@router.post("/{plan_id}/effectiveness-review", operation_id="pac_record_effectiveness_review")
def record_effectiveness_review(plan_id: str, body: EffectivenessReviewBody = Body(...)):
    try:
        result = build_record_effectiveness_review_use_case().execute(
            plan_id,
            EffectivenessReviewRequest(
                effectiveness_status=body.effectiveness_status,
                notes=body.notes,
            ),
            updated_by=_current_user_id(),
        )
        if not result:
            return not_found_response("Plano de ação não encontrado.")
        return success_response(result, message="Eficácia registrada.")
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except PluginsRepositoryError:
        logger.exception("Erro ao registrar eficácia do plano %s.", plan_id)
        return error_response("Erro ao registrar eficácia.", status_code=500, code="PAC_REPOSITORY_ERROR")


@router.post(
    "/{plan_id}/effectiveness-review/submit",
    operation_id="pac_submit_effectiveness_review",
)
def submit_effectiveness_review(plan_id: str, body: SubmitEffectivenessReviewBody = Body(...)):
    try:
        result = build_submit_effectiveness_review_use_case().execute(
            plan_id,
            EffectivenessReviewRequest(
                effectiveness_status=body.effectiveness_status,
                notes=body.notes,
            ),
            updated_by=_current_user_id(),
        )
        if not result:
            return not_found_response("Plano de ação não encontrado.")
        return success_response(result, message="Eficácia submetida para aprovação.")
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except PluginsRepositoryError:
        logger.exception("Erro ao submeter eficácia do plano %s.", plan_id)
        return error_response("Erro ao submeter eficácia.", status_code=500, code="PAC_REPOSITORY_ERROR")


@router.patch("/{plan_id}", operation_id="pac_update_action_plan")
def update_action_plan(plan_id: str, body: UpdateActionPlanBody = Body(...)):
    try:
        fields = body.model_dump(exclude_unset=True)
        if not fields:
            plan = build_get_quality_action_plan_use_case().execute(plan_id)
            if not plan:
                return not_found_response("Plano de ação não encontrado.")
            return success_response(plan, message="Nenhuma alteração informada.")
        result = build_update_quality_action_plan_use_case().execute(
            plan_id,
            UpdateQualityActionPlanRequest(**fields),
            updated_by=_current_user_id(),
        )
        if not result:
            return not_found_response("Plano de ação não encontrado.")
        return success_response(result, message="Plano atualizado.")
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except PluginsRepositoryError:
        logger.exception("Erro ao atualizar plano PAC %s.", plan_id)
        return error_response("Erro ao atualizar plano.", status_code=500, code="PAC_REPOSITORY_ERROR")


@router.patch("/{plan_id}/status", operation_id="pac_update_action_plan_status")
def update_action_plan_status(plan_id: str, body: UpdateActionPlanStatusBody = Body(...)):
    try:
        use_case = build_update_quality_action_plan_status_use_case()
        plan = use_case.execute(
            plan_id,
            status=body.status,
            updated_by=_current_user_id(),
            comment=body.comment,
        )
        if not plan:
            return not_found_response("Plano de ação não encontrado.")
        return success_response(plan, message="Status atualizado com sucesso.")
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except PluginsRepositoryError:
        logger.exception("Erro de persistência ao atualizar status do plano %s.", plan_id)
        return error_response(
            "Erro ao atualizar status do plano.",
            status_code=500,
            code="PAC_REPOSITORY_ERROR",
        )


@router.post("/{plan_id}/reopen", operation_id="pac_reopen_action_plan")
def reopen_action_plan(plan_id: str, body: ReopenActionPlanBody = Body(...)):
    try:
        plan = build_reopen_quality_action_plan_use_case().execute(
            plan_id,
            reason=body.reason,
            target_status=body.target_status,
            updated_by=_current_user_id(),
        )
        if not plan:
            return not_found_response("Plano de ação não encontrado.")
        return success_response(plan, message="Plano reaberto com sucesso.")
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except PluginsRepositoryError:
        logger.exception("Erro ao reabrir plano PAC %s.", plan_id)
        return error_response("Erro ao reabrir plano.", status_code=500, code="PAC_REPOSITORY_ERROR")


@router.put("/{plan_id}/rnc-8d", operation_id="pac_upsert_rnc_8d")
def upsert_rnc_8d_report(plan_id: str, body: Rnc8dReportBody = Body(...)):
    try:
        repo = build_quality_action_plan_repository()
        result = repo.upsert_rnc_8d_report(
            plan_id,
            {
                "customer_template": "rnc_8d",
                "client_nc_registry": body.client_nc_registry,
                "customer_name": body.customer_name,
                "customer_contact": body.customer_contact,
                "product_code": body.product_code,
                "product_description": body.product_description,
                "batch_number": body.batch_number,
                "reported_problem": body.reported_problem,
                "template_payload": body.template_payload,
                "team_members": [member.model_dump() for member in body.team_members]
                if body.team_members is not None
                else None,
            },
            updated_by=_current_user_id(),
        )
        if not result:
            return not_found_response("Plano de ação não encontrado.")
        return success_response(result, message="Relatório 8D salvo.")
    except PluginsRepositoryError:
        logger.exception("Erro ao salvar relatório 8D do plano %s.", plan_id)
        return error_response("Erro ao salvar relatório 8D.", status_code=500, code="PAC_REPOSITORY_ERROR")


@router.get("/{plan_id}/export/rnc-8d", operation_id="pac_export_rnc_8d")
def export_rnc_8d_spreadsheet(plan_id: str):
    try:
        repo = build_quality_action_plan_repository()
        detail = repo.get_plan_detail(plan_id)
        if not detail:
            return not_found_response("Plano de ação não encontrado.")
        storage = PacEvidenceStorage()
        image_annexes = collect_image_annexes_for_export(
            plan_id=plan_id,
            evidences=detail.get("evidences") or [],
            storage=storage,
        )
        content = build_rnc_8d_workbook(detail, image_annexes=image_annexes)
        plan = detail.get("plan") or {}
        registry = plan.get("client_nc_registry") or plan.get("code") or plan_id[:8]
        filename = f"RNC_{registry}_8D.xlsx"
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except FileNotFoundError as exc:
        return error_response(str(exc), status_code=500)
    except Exception:
        logger.exception("Erro ao exportar relatório 8D do plano %s.", plan_id)
        return error_response("Erro ao gerar planilha 8D.", status_code=500)


@router.get("/{plan_id}/evidences", operation_id="pac_list_plan_evidences")
def list_plan_evidences(plan_id: str):
    try:
        repo = build_quality_action_plan_repository()
        if not repo.get_plan_by_id(plan_id):
            return not_found_response("Plano de ação não encontrado.")
        return success_response(repo.list_evidences(plan_id))
    except PluginsRepositoryError:
        logger.exception("Erro ao listar evidências do plano %s.", plan_id)
        return error_response("Erro ao listar evidências.", status_code=500, code="PAC_REPOSITORY_ERROR")


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
    try:
        content = await file.read()
        storage = PacEvidenceStorage()
        storage.validate_upload(mime_type=file.content_type, size_bytes=len(content))
        stored_name = storage.save(
            plan_id=plan_id,
            original_name=file.filename or "evidence.bin",
            content=content,
            mime_type=file.content_type,
        )
        repo = build_quality_action_plan_repository()
        if action_id and not repo.action_belongs_to_plan(plan_id, action_id):
            storage.delete_file(plan_id=plan_id, stored_name=stored_name)
            return error_response("Ação não pertence a este plano.", status_code=422)
        data = repo.create_evidence(
            plan_id,
            {
                "type": evidence_type,
                "file_name": file.filename,
                "stored_name": stored_name,
                "mime_type": file.content_type,
                "size_bytes": len(content),
                "section": section,
                "description": description,
                "knowledge_visible": knowledge_visible,
                "uploaded_by": _current_user_id(),
                "action_id": action_id,
            },
        )
        if not data:
            storage.delete_file(plan_id=plan_id, stored_name=stored_name)
            return not_found_response("Plano de ação não encontrado.")
        return success_response(data, message="Evidência anexada com sucesso.")
    except (PluginsRepositoryError, PacEvidenceStorageError) as exc:
        return error_response(str(exc), status_code=422)
    except Exception:
        logger.exception("Erro ao anexar evidência ao plano %s.", plan_id)
        return error_response("Erro interno ao anexar evidência.", status_code=500)


@router.get("/{plan_id}/evidences/{evidence_id}/file", operation_id="pac_download_plan_evidence")
def download_plan_evidence(plan_id: str, evidence_id: str):
    try:
        repo = build_quality_action_plan_repository()
        evidence = repo.get_evidence(plan_id, evidence_id)
        if not evidence or not evidence.get("stored_name"):
            return not_found_response("Evidência não encontrada.")
        storage = PacEvidenceStorage()
        file_path = storage.resolve_file(
            plan_id=plan_id,
            stored_name=str(evidence["stored_name"]),
        )
        return FileResponse(
            path=file_path,
            media_type=evidence.get("mime_type") or "application/octet-stream",
            filename=str(evidence.get("file_name") or evidence["stored_name"]),
        )
    except (PluginsRepositoryError, PacEvidenceStorageError) as exc:
        return error_response(str(exc), status_code=404)
    except Exception:
        logger.exception("Erro ao baixar evidência %s.", evidence_id)
        return error_response("Erro interno ao baixar evidência.", status_code=500)


@router.delete("/{plan_id}/evidences/{evidence_id}", operation_id="pac_delete_plan_evidence")
def delete_plan_evidence(plan_id: str, evidence_id: str):
    try:
        repo = build_quality_action_plan_repository()
        evidence = repo.delete_evidence(plan_id, evidence_id)
        if not evidence:
            return not_found_response("Evidência não encontrada.")
        if evidence.get("stored_name"):
            try:
                PacEvidenceStorage().delete_file(
                    plan_id=plan_id,
                    stored_name=str(evidence["stored_name"]),
                )
            except PacEvidenceStorageError:
                pass
        return success_response({"id": evidence_id, "deleted": True}, message="Evidência removida.")
    except PluginsRepositoryError:
        logger.exception("Erro ao remover evidência %s.", evidence_id)
        return error_response("Erro ao remover evidência.", status_code=500, code="PAC_REPOSITORY_ERROR")
