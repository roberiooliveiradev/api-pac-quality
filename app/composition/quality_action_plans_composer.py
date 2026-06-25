from app.application.use_cases.quality_action_plans_use_cases import (
    CreateQualityActionPlanUseCase,
    GetQualityActionPlanUseCase,
    ListQualityActionPlansUseCase,
    UpdateQualityActionPlanStatusUseCase,
    UpdateQualityActionPlanUseCase,
)
from app.application.use_cases.quality_action_plan_analysis_use_cases import (
    CreatePlanActionsUseCase,
    GetPlanDetailUseCase,
    RecordEffectivenessReviewUseCase,
    UpdatePlanActionUseCase,
    UpsertFiveWhysUseCase,
    UpsertIshikawaUseCase,
)
from app.composition.quality_intelligence_composer import (
    build_sync_case_similarity_index_use_case,
    build_upsert_solution_pattern_from_plan_use_case,
)
from app.infrastructure.persistence.repositories.postgres_quality_action_plan_repository import (
    PostgresQualityActionPlanRepository,
)


def build_quality_action_plan_repository() -> PostgresQualityActionPlanRepository:
    return PostgresQualityActionPlanRepository()


def build_create_quality_action_plan_use_case() -> CreateQualityActionPlanUseCase:
    return CreateQualityActionPlanUseCase(
        build_quality_action_plan_repository(),
        intelligence_sync=build_sync_case_similarity_index_use_case(),
    )


def build_get_quality_action_plan_use_case() -> GetQualityActionPlanUseCase:
    return GetQualityActionPlanUseCase(build_quality_action_plan_repository())


def build_list_quality_action_plans_use_case() -> ListQualityActionPlansUseCase:
    return ListQualityActionPlansUseCase(build_quality_action_plan_repository())


def build_update_quality_action_plan_status_use_case() -> UpdateQualityActionPlanStatusUseCase:
    return UpdateQualityActionPlanStatusUseCase(build_quality_action_plan_repository())


def build_update_quality_action_plan_use_case() -> UpdateQualityActionPlanUseCase:
    return UpdateQualityActionPlanUseCase(build_quality_action_plan_repository())


def build_upsert_ishikawa_use_case() -> UpsertIshikawaUseCase:
    return UpsertIshikawaUseCase(build_quality_action_plan_repository())


def build_upsert_five_whys_use_case() -> UpsertFiveWhysUseCase:
    return UpsertFiveWhysUseCase(
        build_quality_action_plan_repository(),
        intelligence_sync=build_sync_case_similarity_index_use_case(),
    )


def build_create_plan_actions_use_case() -> CreatePlanActionsUseCase:
    return CreatePlanActionsUseCase(build_quality_action_plan_repository())


def build_get_plan_detail_use_case() -> GetPlanDetailUseCase:
    return GetPlanDetailUseCase(build_quality_action_plan_repository())


def build_record_effectiveness_review_use_case() -> RecordEffectivenessReviewUseCase:
    return RecordEffectivenessReviewUseCase(
        build_quality_action_plan_repository(),
        intelligence_sync=build_sync_case_similarity_index_use_case(),
        pattern_upsert=build_upsert_solution_pattern_from_plan_use_case(),
    )


def build_update_plan_action_use_case() -> UpdatePlanActionUseCase:
    return UpdatePlanActionUseCase(build_quality_action_plan_repository())
