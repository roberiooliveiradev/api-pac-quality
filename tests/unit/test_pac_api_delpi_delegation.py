from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.application.services.pac_api_delpi_delegation_service import PacApiDelpiDelegationService
from app.config import settings
from app.domain.services.pac_delpi_operation_mapping import DELPI_TO_PAC_OPERATION_ID
from tests.unit.test_pac_delpi_read_parity import READ_PARITY
from tests.unit.test_pac_delpi_write_parity import WRITE_PARITY


def test_delpi_to_pac_mapping_matches_parity_modules() -> None:
    expected = {**READ_PARITY, **WRITE_PARITY}
    for delpi_op, pac_op in expected.items():
        assert DELPI_TO_PAC_OPERATION_ID[delpi_op] == pac_op


def test_delegation_disabled_without_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "PAC_DELEGATE_TRANSACTIONAL_TO_API_DELPI", False)
    gateway = MagicMock()
    gateway.configured = True
    service = PacApiDelpiDelegationService(gateway=gateway)
    assert service.forward_json(
        method="GET",
        path_suffix="",
        pac_operation_id="pac_list_action_plans",
    ) is None
    gateway.request_json.assert_not_called()


def test_delegation_rewrites_operation_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "PAC_DELEGATE_TRANSACTIONAL_TO_API_DELPI", True)
    gateway = MagicMock()
    gateway.configured = True
    gateway.request_json.return_value = (
        200,
        {},
        {
            "success": True,
            "message": "ok",
            "data": {"id": "p1"},
            "meta": {"operationId": "create_quality_action_plan"},
        },
    )
    service = PacApiDelpiDelegationService(gateway=gateway)
    response = service.forward_json(
        method="POST",
        path_suffix="",
        pac_operation_id="pac_create_action_plan",
        json_body={"title": "Teste"},
    )
    assert response is not None
    assert response.status_code == 200
    body = response.body.decode()
    assert "pac_create_action_plan" in body
    assert "create_quality_action_plan" not in body
