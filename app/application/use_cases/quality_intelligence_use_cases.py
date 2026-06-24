from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.services.quality_intelligence.case_similarity_scoring_service import (
    CaseSimilarityScoringService,
    IndexedCaseCandidate,
    SimilarCaseQuery,
)
from app.domain.services.quality_intelligence.solution_pattern_ranking_service import (
    SolutionPatternRankingService,
)
from app.infrastructure.persistence.repositories.postgres_quality_intelligence_repository import (
    PostgresQualityIntelligenceRepository,
)


@dataclass(frozen=True)
class SimilarCasesRequest:
    problem_description: str
    product_code: str | None = None
    customer_name: str | None = None
    batch_number: str | None = None
    symptoms: list[str] | None = None
    failure_mode: str | None = None
    root_cause_category: str | None = None
    problem_category: str | None = None
    branch_code: str | None = None


@dataclass(frozen=True)
class SolutionPatternSearchRequest:
    problem_category: str | None = None
    failure_mode: str | None = None
    root_cause_category: str | None = None
    symptom_tags: list[str] | None = None


@dataclass(frozen=True)
class SuggestActionsRequest:
    problem_description: str
    problem_category: str | None = None
    failure_mode: str | None = None
    root_cause_category: str | None = None
    symptom_tags: list[str] | None = None


class SearchSimilarCasesUseCase:
    def __init__(
        self,
        repository: PostgresQualityIntelligenceRepository,
        scoring: CaseSimilarityScoringService | None = None,
    ) -> None:
        self._repository = repository
        self._scoring = scoring or CaseSimilarityScoringService()

    def execute(self, request: SimilarCasesRequest) -> dict[str, Any]:
        if not request.problem_description.strip():
            raise ValueError("problem_description é obrigatório.")

        query = SimilarCaseQuery(
            problem_description=request.problem_description.strip(),
            product_code=request.product_code,
            customer_name=request.customer_name,
            batch_number=request.batch_number,
            symptoms=tuple(request.symptoms or ()),
            failure_mode=request.failure_mode,
            root_cause_category=request.root_cause_category,
            problem_category=request.problem_category,
            branch_code=request.branch_code,
        )

        raw_candidates = self._repository.fetch_similar_case_candidates(
            problem_description=query.problem_description,
            product_code=query.product_code,
            symptoms=list(query.symptoms),
            branch_code=query.branch_code,
        )
        candidates = [
            IndexedCaseCandidate(
                plan_id=item["plan_id"],
                plan_code=item["plan_code"],
                search_text=item["search_text"],
                product_code=item.get("product_code"),
                failure_mode=item.get("failure_mode"),
                root_cause_category=item.get("root_cause_category"),
                symptom_tags=item.get("symptom_tags") or [],
                problem_summary=item.get("problem_summary") or "",
                root_cause=item.get("root_cause"),
                effectiveness_status=item.get("effectiveness_status"),
                closed_at=item.get("closed_at"),
                effective_actions=item.get("effective_actions") or [],
                branch_code=item.get("branch_code"),
            )
            for item in raw_candidates
        ]

        similar_cases = self._scoring.rank_cases(query, candidates)
        recurrence = self._scoring.recurrence_signals(query, candidates)

        return {
            "similar_cases": similar_cases,
            "recurrence_signals": recurrence,
            "suggested_focus_areas": self._scoring.suggested_focus_areas(similar_cases),
        }


class SearchSolutionPatternsUseCase:
    def __init__(
        self,
        repository: PostgresQualityIntelligenceRepository,
        ranking: SolutionPatternRankingService | None = None,
    ) -> None:
        self._repository = repository
        self._ranking = ranking or SolutionPatternRankingService()

    def execute(self, request: SolutionPatternSearchRequest) -> dict[str, Any]:
        patterns = self._repository.list_solution_patterns()
        ranked = self._ranking.rank_patterns(
            patterns,
            problem_category=request.problem_category,
            failure_mode=request.failure_mode,
            root_cause_category=request.root_cause_category,
            symptom_tags=request.symptom_tags or [],
        )
        if ranked:
            self._repository.increment_pattern_usage([p["id"] for p in ranked[:5]])
        return {"patterns": ranked}


class SuggestActionsUseCase:
    def __init__(
        self,
        repository: PostgresQualityIntelligenceRepository,
        case_scoring: CaseSimilarityScoringService | None = None,
        pattern_ranking: SolutionPatternRankingService | None = None,
    ) -> None:
        self._repository = repository
        self._case_scoring = case_scoring or CaseSimilarityScoringService()
        self._pattern_ranking = pattern_ranking or SolutionPatternRankingService()

    def execute(self, request: SuggestActionsRequest) -> dict[str, Any]:
        if not request.problem_description.strip():
            raise ValueError("problem_description é obrigatório.")

        similar_uc = SearchSimilarCasesUseCase(self._repository, self._case_scoring)
        similar_result = similar_uc.execute(
            SimilarCasesRequest(
                problem_description=request.problem_description,
                problem_category=request.problem_category,
                failure_mode=request.failure_mode,
                root_cause_category=request.root_cause_category,
                symptom_tags=request.symptom_tags,
            )
        )

        patterns = self._pattern_ranking.rank_patterns(
            self._repository.list_solution_patterns(),
            problem_category=request.problem_category,
            failure_mode=request.failure_mode,
            root_cause_category=request.root_cause_category,
            symptom_tags=request.symptom_tags or [],
            limit=5,
        )

        suggestions: list[dict[str, Any]] = []
        seen_descriptions: set[str] = set()

        for pattern in patterns:
            for description in pattern.get("recommended_actions") or []:
                key = description.strip().lower()
                if not key or key in seen_descriptions:
                    continue
                seen_descriptions.add(key)
                suggestions.append(
                    {
                        "action_type": "corrective",
                        "description": description,
                        "based_on_cases": [],
                        "based_on_patterns": [pattern["id"]],
                        "historical_effectiveness": pattern.get("effectiveness_rate"),
                        "confidence": "high" if (pattern.get("effectiveness_rate") or 0) >= 0.7 else "medium",
                    }
                )

        for case in similar_result.get("similar_cases") or []:
            for description in case.get("effective_actions") or []:
                key = description.strip().lower()
                if not key or key in seen_descriptions:
                    continue
                seen_descriptions.add(key)
                confidence = "high" if case.get("effectiveness_status") == "effective" else "medium"
                suggestions.append(
                    {
                        "action_type": "corrective",
                        "description": description,
                        "based_on_cases": [case.get("plan_id")],
                        "based_on_patterns": [],
                        "historical_effectiveness": 1.0 if confidence == "high" else 0.5,
                        "confidence": confidence,
                    }
                )

        warnings: list[str] = []
        recurrence = similar_result.get("recurrence_signals") or {}
        if recurrence.get("same_symptom", 0) >= 3:
            warnings.append(
                f"Existem {recurrence['same_symptom']} casos com sintomas semelhantes no histórico."
            )
        not_verified = [
            c
            for c in similar_result.get("similar_cases") or []
            if c.get("effectiveness_status") in {None, "not_verified", "pending"}
        ]
        if len(not_verified) >= 2:
            warnings.append(
                f"Existem {len(not_verified)} casos parecidos encerrados sem verificação de eficácia."
            )

        return {
            "suggestions": suggestions[:10],
            "warnings": warnings,
            "similar_cases": similar_result.get("similar_cases") or [],
        }


class SyncCaseSimilarityIndexUseCase:
    def __init__(self, repository: PostgresQualityIntelligenceRepository) -> None:
        self._repository = repository

    def execute(self, plan_id: str) -> None:
        self._repository.sync_case_similarity_index(plan_id)


class UpsertSolutionPatternFromPlanUseCase:
    def __init__(self, repository: PostgresQualityIntelligenceRepository) -> None:
        self._repository = repository

    def execute(self, plan_id: str) -> dict[str, Any] | None:
        return self._repository.upsert_solution_pattern_from_plan(plan_id)
