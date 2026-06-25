from __future__ import annotations

from unittest.mock import MagicMock

from app.infrastructure.persistence.repositories.postgres_quality_action_plan_repository import (
    PostgresQualityActionPlanRepository,
)


def test_list_plan_audit_log_maps_rows():
    repo = PostgresQualityActionPlanRepository(connection=MagicMock())
    repo._plan_exists = MagicMock(return_value=True)  # noqa: SLF001
    repo.fetch_one = MagicMock(return_value={"total": 1})
    repo.fetch_all = MagicMock(
        return_value=[
            {
                "id": "log-1",
                "event_type": "plan_created",
                "payload": {"code": "PAC-2026-0001"},
                "actor_user_id": "user-1",
                "created_at": None,
            }
        ]
    )

    result = repo.list_plan_audit_log("plan-1")

    assert result["pagination"]["total"] == 1
    assert result["items"][0]["event_type"] == "plan_created"


def test_list_pending_effectiveness_reviews_maps_plans():
    repo = PostgresQualityActionPlanRepository(connection=MagicMock())
    repo.fetch_one = MagicMock(return_value={"total": 1})
    repo.fetch_all = MagicMock(
        return_value=[
            {
                "id": "plan-1",
                "code": "PAC-2026-0002",
                "title": "Oxidação",
                "effectiveness_approval_status": "pending_review",
            }
        ]
    )

    result = repo.list_pending_effectiveness_reviews(page=1, page_size=20)

    assert result["pagination"]["total"] == 1
    assert result["items"][0]["code"] == "PAC-2026-0002"
