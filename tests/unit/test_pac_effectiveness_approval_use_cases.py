from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.application.use_cases.quality_action_plan_analysis_use_cases import (
    ApproveEffectivenessReviewUseCase,
    EffectivenessReviewRequest,
    RejectEffectivenessReviewUseCase,
    SubmitEffectivenessReviewUseCase,
)


def test_submit_effectiveness_review_blocks_invalid_status():
    use_case = SubmitEffectivenessReviewUseCase(MagicMock())
    with pytest.raises(ValueError, match="submissão"):
        use_case.execute(
            "plan-1",
            EffectivenessReviewRequest(effectiveness_status="pending"),
            updated_by="user-1",
        )


def test_submit_effectiveness_review_delegates_to_repository():
    repo = MagicMock()
    repo.submit_effectiveness_review.return_value = {"id": "plan-1"}
    use_case = SubmitEffectivenessReviewUseCase(repo)

    result = use_case.execute(
        "plan-1",
        EffectivenessReviewRequest(effectiveness_status="effective", notes="ok"),
        updated_by="user-1",
    )

    assert result["id"] == "plan-1"
    repo.submit_effectiveness_review.assert_called_once()


def test_reject_effectiveness_review_requires_reason():
    use_case = RejectEffectivenessReviewUseCase(MagicMock())
    with pytest.raises(ValueError, match="motivo"):
        use_case.execute("plan-1", reason="abc", updated_by="coord-1")


def test_approve_effectiveness_review_triggers_sync():
    repo = MagicMock()
    repo.approve_effectiveness_review.return_value = {"id": "plan-1"}
    sync = MagicMock()
    use_case = ApproveEffectivenessReviewUseCase(repo, intelligence_sync=sync)

    use_case.execute("plan-1", updated_by="coord-1")

    sync.execute.assert_called_once_with("plan-1")
