from __future__ import annotations

import logging

from fastapi import APIRouter, Body
from pydantic import BaseModel, Field

from delpi_auth.authorization import require_any_permission

from app.application.security.pac_quality_permissions import (
    QUALITY_ACTION_PLANS_READ_PERMISSIONS,
    QUALITY_ACTION_PLANS_WRITE_PERMISSIONS,
)
from app.application.use_cases.quality_intelligence_use_cases import (
    SearchSimilarCasesUseCase,
    SearchSolutionPatternsUseCase,
    SimilarCasesRequest,
    SolutionPatternSearchRequest,
    SuggestActionsRequest,
    SuggestActionsUseCase,
)
from app.composition.quality_intelligence_composer import (
    build_search_similar_cases_use_case,
    build_search_solution_patterns_use_case,
    build_suggest_actions_use_case,
)
from app.core.responses import error_response, success_response
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
