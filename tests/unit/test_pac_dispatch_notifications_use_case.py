from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.application.use_cases.dispatch_pac_quality_notifications_use_case import (
    DispatchPacQualityNotificationsUseCase,
)


@patch(
    "app.application.use_cases.dispatch_pac_quality_notifications_use_case.pac_portal_notifications_enabled",
    return_value=False,
)
def test_dispatch_notifications_disabled(_mock_enabled):
    use_case = DispatchPacQualityNotificationsUseCase(MagicMock())
    result = use_case.execute(dry_run=True)

    assert result.enabled is False
    assert result.sent == 0


@patch(
    "app.application.use_cases.dispatch_pac_quality_notifications_use_case.pac_portal_notifications_enabled",
    return_value=True,
)
@patch(
    "app.application.use_cases.dispatch_pac_quality_notifications_use_case.send_pac_portal_notification",
    return_value=True,
)
def test_dispatch_notifications_dry_run_counts_candidates(_mock_send, _mock_enabled):
    repo = MagicMock()
    repo.list_actions_due_within_days.return_value = [
        {
            "action_id": "a1",
            "plan_id": "p1",
            "description": "Conter lote",
            "due_date": "2026-06-26",
            "responsible_user_id": "user-1",
            "plan_code": "PAC-2026-0001",
        }
    ]
    repo.list_stalled_critical_plans.return_value = []
    repo.notification_already_sent.return_value = False

    result = DispatchPacQualityNotificationsUseCase(repo).execute(dry_run=True)

    assert result.enabled is True
    assert result.candidates == 1
    assert result.sent == 1
    _mock_send.assert_not_called()
