from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.application.use_cases.quality_action_plans_use_cases import ReopenQualityActionPlanUseCase


def test_reopen_requires_reason():
    use_case = ReopenQualityActionPlanUseCase(MagicMock())
    with pytest.raises(ValueError, match="motivo"):
        use_case.execute("plan-1", reason="abc", updated_by="user-1")


def test_reopen_defaults_target_for_completed():
    repo = MagicMock()
    repo.get_plan_by_id.return_value = {"id": "plan-1", "status": "completed"}
    repo.reopen_plan.return_value = {"id": "plan-1", "status": "in_progress"}
    use_case = ReopenQualityActionPlanUseCase(repo)

    result = use_case.execute(
        "plan-1",
        reason="Nova evidência do cliente",
        updated_by="user-1",
    )

    assert result["status"] == "in_progress"
    repo.reopen_plan.assert_called_once_with(
        "plan-1",
        target_status="in_progress",
        reason="Nova evidência do cliente",
        updated_by="user-1",
    )
