from unittest.mock import MagicMock

from app.application.use_cases.quality_intelligence_use_cases import (
    SearchSimilarCasesUseCase,
    SimilarCasesRequest,
    SuggestActionsRequest,
    SuggestActionsUseCase,
)
from app.domain.services.quality_intelligence.case_similarity_decision_log_service import (
    CaseSimilarityDecisionLogService,
)
from app.domain.services.quality_intelligence.case_similarity_scoring_service import (
    CaseSimilarityScoringService,
    IndexedCaseCandidate,
)


def _candidate(**overrides) -> IndexedCaseCandidate:
    base = {
        "plan_id": "uuid-1",
        "plan_code": "PAC-2026-0100",
        "search_text": "oxidação parafuso campo cliente",
        "product_code": "90110001",
        "failure_mode": "oxidação",
        "root_cause_category": "processo",
        "symptom_tags": ["oxidação"],
        "problem_summary": "Oxidação em parafusos",
        "root_cause": "Tratamento superficial insuficiente",
        "effectiveness_status": "effective",
        "closed_at": "2026-05-01",
        "effective_actions": ["Revisar processo de tratamento"],
        "branch_code": "01",
    }
    base.update(overrides)
    return IndexedCaseCandidate(**base)


def test_search_similar_cases_includes_decision_log():
    repository = MagicMock()
    repository.fetch_similar_case_candidates.return_value = [
        {
            "plan_id": "uuid-1",
            "plan_code": "PAC-2026-0100",
            "search_text": "oxidação parafuso campo cliente",
            "product_code": "90110001",
            "failure_mode": "oxidação",
            "root_cause_category": "processo",
            "symptom_tags": ["oxidação"],
            "problem_summary": "Oxidação em parafusos",
            "root_cause": "Tratamento superficial insuficiente",
            "effectiveness_status": "effective",
            "closed_at": "2026-05-01",
            "effective_actions": ["Revisar processo de tratamento"],
            "branch_code": "01",
        }
    ]

    result = SearchSimilarCasesUseCase(repository).execute(
        SimilarCasesRequest(
            problem_description="oxidação em parafusos após campo",
            product_code="90110001",
            branch_code="01",
            symptoms=["oxidação"],
        )
    )

    log = result["similar_cases_decision_log"]
    assert log["entries"]
    assert log["entries"][0]["influence_factors"]
    assert "product_match" in {f["key"] for f in log["entries"][0]["influence_factors"]}
    assert result["similar_cases"][0]["influence_factors"]


def test_suggest_actions_marks_influenced_plan_uuids():
    repository = MagicMock()
    repository.fetch_similar_case_candidates.return_value = [
        {
            "plan_id": "uuid-1",
            "plan_code": "PAC-2026-0100",
            "search_text": "oxidação parafuso",
            "product_code": "90110001",
            "failure_mode": None,
            "root_cause_category": None,
            "symptom_tags": [],
            "problem_summary": "Oxidação",
            "root_cause": None,
            "effectiveness_status": "effective",
            "closed_at": None,
            "effective_actions": ["Ajustar tratamento superficial"],
            "branch_code": "01",
        }
    ]
    repository.list_solution_patterns.return_value = []

    result = SuggestActionsUseCase(repository).execute(
        SuggestActionsRequest(problem_description="oxidação em parafusos")
    )

    log = result["similar_cases_decision_log"]
    assert "uuid-1" in log["influenced_plan_uuids"]
    assert log["entries"][0]["influenced_suggestion"] is True


def test_score_breakdown_lists_factors():
    scoring = CaseSimilarityScoringService()
    from app.domain.services.quality_intelligence.case_similarity_scoring_service import (
        SimilarCaseQuery,
    )

    query = SimilarCaseQuery(
        problem_description="oxidação parafuso",
        product_code="90110001",
        branch_code="01",
    )
    total, factors = scoring.score_breakdown(query, _candidate())

    assert total >= 0.27
    assert {item["key"] for item in factors} >= {"product_match", "branch_match"}


def test_decision_log_service_builds_top_plan_ids():
    from app.domain.services.quality_intelligence.case_similarity_scoring_service import (
        SimilarCaseQuery,
    )

    query = SimilarCaseQuery(problem_description="teste")
    ranked = [
        {"plan_id": "PAC-1", "plan_uuid": "u1", "similarity_score": 0.5, "influence_factors": []},
        {"plan_id": "PAC-2", "plan_uuid": "u2", "similarity_score": 0.4, "influence_factors": []},
    ]

    log = CaseSimilarityDecisionLogService().build_from_ranked_cases(
        query,
        ranked,
        influenced_plan_uuids={"u2"},
    )

    assert log["top_plan_ids"] == ["PAC-1", "PAC-2"]
    assert log["entries"][1]["influenced_suggestion"] is True
