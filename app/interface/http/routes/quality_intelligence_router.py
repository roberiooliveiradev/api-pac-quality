from __future__ import annotations

import logging

from fastapi import APIRouter, Body, File, Form, UploadFile
from pydantic import BaseModel, Field

from delpi_auth.authorization import require_any_permission

from app.application.security.pac_quality_permissions import (
    QUALITY_ACTION_PLANS_READ_PERMISSIONS,
    QUALITY_ACTION_PLANS_WRITE_PERMISSIONS,
)
from app.application.use_cases.quality_intelligence_use_cases import (
    AssessRecurrenceOnOpeningRequest,
    SearchSimilarCasesUseCase,
    SearchSolutionPatternsUseCase,
    SimilarCasesRequest,
    SolutionPatternSearchRequest,
    SuggestActionsRequest,
    SuggestActionsUseCase,
)
from app.composition.quality_intelligence_composer import (
    build_assess_recurrence_on_opening_use_case,
    build_search_similar_cases_use_case,
    build_search_solution_patterns_use_case,
    build_suggest_actions_use_case,
)
from app.core.responses import error_response, success_response
from app.domain.services.quality_intelligence.pac_evidence_ocr_tag_suggestion_service import (
    PacEvidenceOcrTagSuggestionService,
)
from app.infrastructure.ocr.pac_evidence_image_ocr_service import PacEvidenceImageOcrService
from app.infrastructure.persistence.plugins.plugin_base_repository import PluginsRepositoryError

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/quality/action-plans/intelligence",
    tags=["PAC Qualidade — inteligência histórica"],
)


class SimilarCasesBody(BaseModel):
    problem_description: str = Field(..., min_length=3)
    product_code: str | None = None
    customer_name: str | None = None
    batch_number: str | None = None
    symptoms: list[str] | None = None
    failure_mode: str | None = None
    root_cause_category: str | None = None
    problem_category: str | None = None
    branch_code: str | None = Field(default=None, pattern="^(01|02)$")


class SolutionPatternSearchBody(BaseModel):
    problem_category: str | None = None
    failure_mode: str | None = None
    root_cause_category: str | None = None
    symptom_tags: list[str] | None = None


class SuggestActionsBody(BaseModel):
    problem_description: str = Field(..., min_length=3)
    problem_category: str | None = None
    failure_mode: str | None = None
    root_cause_category: str | None = None
    symptom_tags: list[str] | None = None


class RecurrenceOpeningAssessmentBody(BaseModel):
    problem_description: str = Field(..., min_length=3)
    product_code: str | None = None
    failure_mode: str | None = None
    branch_code: str | None = Field(default=None, pattern="^(01|02)$")
    symptoms: list[str] | None = None
    root_cause_category: str | None = None
    recurrence_key: str | None = Field(default=None, max_length=500)


class SuggestEvidenceTagsBody(BaseModel):
    ocr_text: str | None = None
    file_name: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=2000)


@router.post("/similar-cases", operation_id="pac_search_similar_cases")
@require_any_permission(QUALITY_ACTION_PLANS_READ_PERMISSIONS)
def search_similar_cases(body: SimilarCasesBody = Body(...)):
    try:
        use_case: SearchSimilarCasesUseCase = build_search_similar_cases_use_case()
        result = use_case.execute(
            SimilarCasesRequest(
                problem_description=body.problem_description,
                product_code=body.product_code,
                customer_name=body.customer_name,
                batch_number=body.batch_number,
                symptoms=body.symptoms,
                failure_mode=body.failure_mode,
                root_cause_category=body.root_cause_category,
                problem_category=body.problem_category,
                branch_code=body.branch_code,
            )
        )
        return success_response(result)
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except PluginsRepositoryError:
        logger.exception("Erro ao buscar casos similares.")
        return error_response(
            "Erro ao consultar histórico de casos.",
            status_code=500,
            code="PAC_INTELLIGENCE_ERROR",
        )


@router.post(
    "/recurrence-opening-assessment",
    operation_id="pac_assess_recurrence_on_opening",
)
@require_any_permission(QUALITY_ACTION_PLANS_READ_PERMISSIONS)
def assess_recurrence_on_opening(body: RecurrenceOpeningAssessmentBody = Body(...)):
    try:
        use_case = build_assess_recurrence_on_opening_use_case()
        result = use_case.execute(
            AssessRecurrenceOnOpeningRequest(
                problem_description=body.problem_description,
                product_code=body.product_code,
                failure_mode=body.failure_mode,
                branch_code=body.branch_code,
                symptoms=body.symptoms,
                root_cause_category=body.root_cause_category,
                recurrence_key=body.recurrence_key,
            )
        )
        return success_response(result)
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except PluginsRepositoryError:
        logger.exception("Erro ao avaliar recorrência na abertura.")
        return error_response(
            "Erro ao avaliar recorrência histórica.",
            status_code=500,
            code="PAC_INTELLIGENCE_ERROR",
        )


def _build_evidence_tag_suggestion(
    *,
    ocr_text: str | None,
    file_name: str | None,
    description: str | None,
    ocr_meta: dict | None = None,
) -> dict:
    suggestion = PacEvidenceOcrTagSuggestionService.suggest(
        ocr_text=ocr_text,
        file_name=file_name,
        description=description,
    )
    suggestion["ocr"] = ocr_meta or {
        "used": bool((ocr_text or "").strip()),
        "reason": "provided_text" if (ocr_text or "").strip() else "none",
    }
    return suggestion


@router.post("/suggest-evidence-tags", operation_id="pac_suggest_evidence_tags")
@require_any_permission(QUALITY_ACTION_PLANS_READ_PERMISSIONS)
def suggest_evidence_tags(body: SuggestEvidenceTagsBody = Body(...)):
    if not any(
        [
            (body.ocr_text or "").strip(),
            (body.file_name or "").strip(),
            (body.description or "").strip(),
        ]
    ):
        return error_response(
            "Informe ao menos ocr_text, file_name ou description.",
            status_code=400,
        )

    return success_response(
        _build_evidence_tag_suggestion(
            ocr_text=body.ocr_text,
            file_name=body.file_name,
            description=body.description,
        )
    )


@router.post(
    "/suggest-evidence-tags/from-image",
    operation_id="pac_suggest_evidence_tags_from_image",
)
@require_any_permission(QUALITY_ACTION_PLANS_READ_PERMISSIONS)
async def suggest_evidence_tags_from_image(
    file: UploadFile = File(...),
    file_name: str | None = Form(default=None),
    description: str | None = Form(default=None),
):
    content = await file.read()
    ocr_meta = PacEvidenceImageOcrService.extract_text_from_bytes(
        content,
        mime_type=file.content_type,
    )
    resolved_name = file_name or file.filename

    return success_response(
        _build_evidence_tag_suggestion(
            ocr_text=ocr_meta.get("text"),
            file_name=resolved_name,
            description=description,
            ocr_meta=ocr_meta,
        )
    )


@router.post("/solution-patterns/search", operation_id="pac_search_solution_patterns")
@require_any_permission(QUALITY_ACTION_PLANS_READ_PERMISSIONS)
def search_solution_patterns(body: SolutionPatternSearchBody = Body(...)):
    try:
        use_case: SearchSolutionPatternsUseCase = build_search_solution_patterns_use_case()
        result = use_case.execute(
            SolutionPatternSearchRequest(
                problem_category=body.problem_category,
                failure_mode=body.failure_mode,
                root_cause_category=body.root_cause_category,
                symptom_tags=body.symptom_tags,
            )
        )
        return success_response(result)
    except PluginsRepositoryError:
        logger.exception("Erro ao buscar padrões de solução.")
        return error_response(
            "Erro ao consultar padrões de solução.",
            status_code=500,
            code="PAC_INTELLIGENCE_ERROR",
        )


@router.post("/suggest-actions", operation_id="pac_suggest_actions")
@require_any_permission(QUALITY_ACTION_PLANS_READ_PERMISSIONS)
def suggest_actions(body: SuggestActionsBody = Body(...)):
    try:
        use_case: SuggestActionsUseCase = build_suggest_actions_use_case()
        result = use_case.execute(
            SuggestActionsRequest(
                problem_description=body.problem_description,
                problem_category=body.problem_category,
                failure_mode=body.failure_mode,
                root_cause_category=body.root_cause_category,
                symptom_tags=body.symptom_tags,
            )
        )
        return success_response(result)
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except PluginsRepositoryError:
        logger.exception("Erro ao sugerir ações.")
        return error_response(
            "Erro ao sugerir ações com base histórica.",
            status_code=500,
            code="PAC_INTELLIGENCE_ERROR",
        )
