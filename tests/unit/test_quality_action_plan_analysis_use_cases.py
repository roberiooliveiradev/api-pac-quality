import pytest

from app.application.use_cases.quality_action_plan_analysis_use_cases import (
    CreateActionItemRequest,
    CreatePlanActionsUseCase,
    UpsertFiveWhysUseCase,
    UpsertFiveWhysRequest,
)
from unittest.mock import MagicMock


def test_five_whys_rejects_invalid_confidence():
    repository = MagicMock()
    use_case = UpsertFiveWhysUseCase(repository)

    with pytest.raises(ValueError, match="confidence_level"):
        use_case.execute(
            "plan-id",
            UpsertFiveWhysRequest(confidence_level="invalid"),
            updated_by="user-1",
        )


def test_create_actions_requires_valid_type():
    repository = MagicMock()
    use_case = CreatePlanActionsUseCase(repository)

    with pytest.raises(ValueError, match="action_type"):
        use_case.execute(
            "plan-id",
            [
                CreateActionItemRequest(
                    action_type="invalid",
                    description="Teste",
                )
            ],
            created_by="user-1",
        )
