from app.domain.services.quality_intelligence.case_similarity_scoring_service import (
    CaseSimilarityScoringService,
    IndexedCaseCandidate,
    SimilarCaseQuery,
)


def test_similarity_boosts_product_and_symptoms():
    service = CaseSimilarityScoringService()
    query = SimilarCaseQuery(
        problem_description="cabo rompeu durante o uso",
        product_code="010101",
        symptoms=("rompimento", "isolacao"),
    )
    candidate = IndexedCaseCandidate(
        plan_id="uuid",
        plan_code="PAC-2026-0001",
        search_text="rompimento de cabo durante uso cliente",
        product_code="010101",
        failure_mode="rompimento de cabo",
        root_cause_category="processo",
        symptom_tags=["rompimento", "isolacao"],
        problem_summary="Rompimento de cabo",
        root_cause="Ferramental desgastado",
        effectiveness_status="effective",
        closed_at="2026-05-14",
        effective_actions=["Rotina preventiva de ferramental"],
    )
    score = service.score(query, candidate)
    assert score >= 0.5

    ranked = service.rank_cases(query, [candidate])
    assert ranked[0]["similarity_score"] == score
    assert ranked[0]["plan_id"] == "PAC-2026-0001"
