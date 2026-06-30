from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.application.services.pac_api_delpi_delegation_service import PacApiDelpiDelegationService
from app.domain.services.pac_delpi_operation_mapping import DELPI_TO_PAC_OPERATION_ID
from tests.unit.test_pac_delpi_read_parity import READ_PARITY
from tests.unit.test_pac_delpi_write_parity import WRITE_PARITY


def test_delpi_to_pac_mapping_matches_parity_modules() -> None:
    expected = {**READ_PARITY, **WRITE_PARITY}
    for delpi_op, pac_op in expected.items():
        assert DELPI_TO_PAC_OPERATION_ID[delpi_op] == pac_op


def test_delegation_misconfigured_without_gateway(monkeypatch: pytest.MonkeyPatch) -> None:
    gateway = MagicMock()
    gateway.configured = False
    service = PacApiDelpiDelegationService(gateway=gateway)
    response = service.forward_json(
        method="GET",
        path_suffix="",
        pac_operation_id="pac_list_action_plans",
    )
    assert response is not None
    assert response.status_code == 503
    gateway.request_json.assert_not_called()


def test_delegation_forward_binary_uses_request_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    gateway = MagicMock()
    gateway.configured = True
    gateway.request_binary.return_value = (
        200,
        {"content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
        b"file-bytes",
    )
    service = PacApiDelpiDelegationService(gateway=gateway)
    response = service.forward_binary(
        method="GET",
        path_suffix="/plan/evidences/e1/file",
        pac_operation_id="pac_download_plan_evidence",
    )
    assert response is not None
    assert response.status_code == 200
    assert response.body == b"file-bytes"
    gateway.request_binary.assert_called_once()
    gateway.request_json.assert_not_called()


def test_delegation_rewrites_operation_id(monkeypatch: pytest.MonkeyPatch) -> None:
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
