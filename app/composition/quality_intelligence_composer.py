from app.application.use_cases.quality_intelligence_use_cases import (
    AssessRecurrenceOnOpeningUseCase,
    PromoteSolutionPatternFromPlanUseCase,
    SearchSimilarCasesUseCase,
    SearchSolutionPatternsUseCase,
    SuggestActionsUseCase,
    SyncCaseSimilarityIndexUseCase,
    UpsertSolutionPatternFromPlanUseCase,
)
from app.infrastructure.embeddings.null_case_similarity_embedding_gateway import (
    NullCaseSimilarityEmbeddingGateway,
)
from app.infrastructure.embeddings.ollama_case_similarity_embedding_gateway import (
    OllamaCaseSimilarityEmbeddingGateway,
)
from app.infrastructure.persistence.repositories.postgres_quality_intelligence_repository import (
    PostgresQualityIntelligenceRepository,
)


def build_quality_intelligence_repository() -> PostgresQualityIntelligenceRepository:
    return PostgresQualityIntelligenceRepository()


def build_case_similarity_embedding_gateway():
    gateway = OllamaCaseSimilarityEmbeddingGateway()
    if gateway.is_enabled():
        return gateway
    return NullCaseSimilarityEmbeddingGateway()


def build_search_similar_cases_use_case() -> SearchSimilarCasesUseCase:
    return SearchSimilarCasesUseCase(
        build_quality_intelligence_repository(),
        embedding_gateway=build_case_similarity_embedding_gateway(),
    )


def build_search_solution_patterns_use_case() -> SearchSolutionPatternsUseCase:
    return SearchSolutionPatternsUseCase(build_quality_intelligence_repository())


def build_suggest_actions_use_case() -> SuggestActionsUseCase:
    return SuggestActionsUseCase(
        build_quality_intelligence_repository(),
        embedding_gateway=build_case_similarity_embedding_gateway(),
    )


def build_sync_case_similarity_index_use_case() -> SyncCaseSimilarityIndexUseCase:
    return SyncCaseSimilarityIndexUseCase(
        build_quality_intelligence_repository(),
        embedding_gateway=build_case_similarity_embedding_gateway(),
    )


def build_upsert_solution_pattern_from_plan_use_case() -> UpsertSolutionPatternFromPlanUseCase:
    return UpsertSolutionPatternFromPlanUseCase(build_quality_intelligence_repository())


def build_promote_solution_pattern_from_plan_use_case() -> PromoteSolutionPatternFromPlanUseCase:
    return PromoteSolutionPatternFromPlanUseCase(build_quality_intelligence_repository())


def build_assess_recurrence_on_opening_use_case() -> AssessRecurrenceOnOpeningUseCase:
    repository = build_quality_intelligence_repository()
    return AssessRecurrenceOnOpeningUseCase(
        repository,
        search_similar_cases=build_search_similar_cases_use_case(),
    )
