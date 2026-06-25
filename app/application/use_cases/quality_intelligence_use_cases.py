from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.services.quality_intelligence.case_similarity_decision_log_service import (
    CaseSimilarityDecisionLogService,
)
from app.domain.services.quality_intelligence.case_similarity_embedding_service import (
    CaseSimilarityEmbeddingPort,
    CaseSimilarityEmbeddingService,
)
from app.domain.services.quality_intelligence.case_similarity_scoring_service import (
    CaseSimilarityScoringService,
    IndexedCaseCandidate,
    SimilarCaseQuery,
)
from app.domain.services.pac_quality_branch_service import (
    build_recurrence_key,
    validate_branch_code,
)
from app.domain.services.quality_intelligence.pac_recurrence_proactive_alert_service import (
    PacRecurrenceProactiveAlertService,
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
        decision_log: CaseSimilarityDecisionLogService | None = None,
        embedding_gateway: CaseSimilarityEmbeddingPort | None = None,
    ) -> None:
        self._repository = repository
        self._scoring = scoring or CaseSimilarityScoringService()
        self._decision_log = decision_log or CaseSimilarityDecisionLogService(self._scoring)
        self._embedding_gateway = embedding_gateway

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

        query_embedding = None
        if self._embedding_gateway is not None:
            query_embedding = CaseSimilarityEmbeddingService.embed_search_text(
                self._embedding_gateway,
                query.problem_description,
            )

        raw_candidates = self._repository.fetch_similar_case_candidates(
            problem_description=query.problem_description,
            product_code=query.product_code,
            symptoms=list(query.symptoms),
            branch_code=query.branch_code,
            query_embedding=query_embedding,
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
                semantic_similarity=item.get("semantic_similarity"),
            )
            for item in raw_candidates
        ]

        similar_cases = self._decision_log.enrich_ranked_cases(query, candidates)
        recurrence = self._scoring.recurrence_signals(query, candidates)

        return {
            "similar_cases": similar_cases,
            "recurrence_signals": recurrence,
            "suggested_focus_areas": self._scoring.suggested_focus_areas(similar_cases),
            "similar_cases_decision_log": self._decision_log.build_from_ranked_cases(
                query,
                similar_cases,
            ),
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
        embedding_gateway: CaseSimilarityEmbeddingPort | None = None,
    ) -> None:
        self._repository = repository
        self._case_scoring = case_scoring or CaseSimilarityScoringService()
        self._pattern_ranking = pattern_ranking or SolutionPatternRankingService()
        self._embedding_gateway = embedding_gateway

    def execute(self, request: SuggestActionsRequest) -> dict[str, Any]:
        if not request.problem_description.strip():
            raise ValueError("problem_description é obrigatório.")

        similar_uc = SearchSimilarCasesUseCase(
            self._repository,
            self._case_scoring,
            embedding_gateway=self._embedding_gateway,
        )
        similar_result = similar_uc.execute(
            SimilarCasesRequest(
                problem_description=request.problem_description,
                problem_category=request.problem_category,
                failure_mode=request.failure_mode,
                root_cause_category=request.root_cause_category,
                symptoms=request.symptom_tags,
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
        influenced_plan_uuids: set[str] = set()

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
                plan_uuid = str(case.get("plan_uuid") or "").strip()
                if plan_uuid:
                    influenced_plan_uuids.add(plan_uuid)
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
            "similar_cases_decision_log": CaseSimilarityDecisionLogService(
                self._case_scoring
            ).build_from_ranked_cases(
                SimilarCaseQuery(
                    problem_description=request.problem_description.strip(),
                    problem_category=request.problem_category,
                    failure_mode=request.failure_mode,
                    root_cause_category=request.root_cause_category,
                    symptoms=tuple(request.symptom_tags or ()),
                ),
                similar_result.get("similar_cases") or [],
                influenced_plan_uuids=influenced_plan_uuids,
            ),
        }


class SyncCaseSimilarityIndexUseCase:
    def __init__(
        self,
        repository: PostgresQualityIntelligenceRepository,
        embedding_gateway: CaseSimilarityEmbeddingPort | None = None,
    ) -> None:
        self._repository = repository
        self._embedding_gateway = embedding_gateway

    def execute(self, plan_id: str) -> None:
        search_text = self._repository.sync_case_similarity_index(plan_id)
        if not search_text or self._embedding_gateway is None:
            return

        embedding = CaseSimilarityEmbeddingService.embed_search_text(
            self._embedding_gateway,
            search_text,
        )
        if embedding:
            self._repository.update_search_embedding(plan_id, embedding)


class UpsertSolutionPatternFromPlanUseCase:
    def __init__(self, repository: PostgresQualityIntelligenceRepository) -> None:
        self._repository = repository

    def execute(self, plan_id: str) -> dict[str, Any] | None:
        return self._repository.upsert_solution_pattern_from_plan(plan_id)


class PromoteSolutionPatternFromPlanUseCase(UpsertSolutionPatternFromPlanUseCase):
    """Alias explícito para paridade com api-delpi (rota promote-solution-pattern)."""


@dataclass(frozen=True)
class AssessRecurrenceOnOpeningRequest:
    problem_description: str
    product_code: str | None = None
    failure_mode: str | None = None
    branch_code: str | None = None
    symptoms: list[str] | None = None
    root_cause_category: str | None = None
    recurrence_key: str | None = None


class AssessRecurrenceOnOpeningUseCase:
    def __init__(
        self,
        repository: PostgresQualityIntelligenceRepository,
        scoring: CaseSimilarityScoringService | None = None,
        search_similar_cases: SearchSimilarCasesUseCase | None = None,
    ) -> None:
        self._repository = repository
        self._scoring = scoring or CaseSimilarityScoringService()
        self._search_similar_cases = search_similar_cases or SearchSimilarCasesUseCase(
            repository,
            self._scoring,
        )

    def execute(self, request: AssessRecurrenceOnOpeningRequest) -> dict[str, Any]:
        if not request.problem_description.strip():
            raise ValueError("problem_description é obrigatório.")

        branch_code = validate_branch_code(request.branch_code, required=False)
        recurrence_key = build_recurrence_key(
            branch_code=branch_code,
            product_code=request.product_code,
            failure_mode=request.failure_mode,
            explicit=request.recurrence_key,
        )

        from app.domain.services.pac_recurrence_alert_content_service import (
            PacRecurrenceAlertContentService,
        )

        window_months = PacRecurrenceAlertContentService.window_months()
        stats = {"plans_in_window": 0, "open_plans": 0, "total_plans": 0}

        if recurrence_key:
            stats = self._repository.fetch_recurrence_opening_stats(
                recurrence_key=recurrence_key,
                branch_code=branch_code,
                window_months=window_months,
            )

        similar_result = self._search_similar_cases.execute(
            SimilarCasesRequest(
                problem_description=request.problem_description.strip(),
                product_code=request.product_code,
                failure_mode=request.failure_mode,
                branch_code=branch_code,
                symptoms=request.symptoms,
                root_cause_category=request.root_cause_category,
            )
        )
        recurrence_signals = similar_result.get("recurrence_signals") or {}

        if not recurrence_key and int(recurrence_signals.get("same_product") or 0) >= 2:
            stats = {
                **stats,
                "plans_in_window": max(
                    stats["plans_in_window"],
                    int(recurrence_signals.get("same_product") or 0),
                ),
                "total_plans": max(
                    stats["total_plans"],
                    int(recurrence_signals.get("same_product") or 0),
                ),
            }

        assessment = PacRecurrenceProactiveAlertService.build_assessment(
            recurrence_key=recurrence_key,
            plans_in_window=stats["plans_in_window"],
            open_plans=stats["open_plans"],
            total_plans=stats["total_plans"],
            recurrence_signals=recurrence_signals,
        )

        return {
            **assessment,
            "similar_cases_preview": (similar_result.get("similar_cases") or [])[:3],
            "similar_cases_decision_log": similar_result.get("similar_cases_decision_log"),
        }


@dataclass(frozen=True)
class KnowledgeGraphRequest:
    branch_code: str | None = None
    product_code: str | None = None
    limit: int | None = None


class GetQualityKnowledgeGraphUseCase:
    def __init__(self, repository: PostgresQualityIntelligenceRepository) -> None:
        self._repository = repository

    def execute(self, request: KnowledgeGraphRequest) -> dict[str, Any]:
        from app.domain.services.quality_intelligence.pac_quality_knowledge_graph_service import (
            PacQualityKnowledgeGraphService,
        )

        rows = self._repository.fetch_knowledge_graph_paths(
            branch_code=request.branch_code,
            product_code=request.product_code,
            limit=request.limit,
        )
        graph = PacQualityKnowledgeGraphService.build(rows)
        graph["filters"] = {
            "branch_code": request.branch_code,
            "product_code": request.product_code,
        }
        return graph
