"""GET plano — referência por UUID ou código PAC."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def plans_client() -> TestClient:
    from app.interface.http.routes.quality_action_plans_router import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@patch("app.interface.http.routes.quality_action_plans_router.build_get_plan_detail_use_case")
def test_get_action_plan_by_code_returns_detail(
    mock_build: MagicMock,
    plans_client: TestClient,
) -> None:
    mock_use_case = MagicMock()
    mock_use_case.execute.return_value = {
        "plan": {"id": "uuid-1", "code": "PAC-2026-0029", "title": "Teste"},
        "ishikawa": None,
        "five_whys": None,
        "actions": [],
    }
    mock_build.return_value = mock_use_case

    response = plans_client.get("/quality/action-plans/PAC-2026-0029")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    mock_use_case.execute.assert_called_once_with("PAC-2026-0029")


@patch("app.interface.http.routes.quality_action_plans_router.build_get_plan_detail_use_case")
def test_get_action_plan_not_found_returns_404(
    mock_build: MagicMock,
    plans_client: TestClient,
) -> None:
    mock_use_case = MagicMock()
    mock_use_case.execute.return_value = None
    mock_build.return_value = mock_use_case

    response = plans_client.get("/quality/action-plans/PAC-2026-9999")
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False


@patch("app.interface.http.routes.quality_action_plans_router.build_list_quality_action_plans_use_case")
def test_list_action_plans_accepts_code_filter(
    mock_build: MagicMock,
    plans_client: TestClient,
) -> None:
    mock_use_case = MagicMock()
    mock_use_case.execute.return_value = {
        "items": [{"id": "uuid-1", "code": "PAC-2026-0029"}],
        "pagination": {"page": 1, "page_size": 50, "total": 1, "total_pages": 1},
    }
    mock_build.return_value = mock_use_case

    response = plans_client.get("/quality/action-plans", params={"code": "PAC-2026-0029"})
    assert response.status_code == 200
    mock_use_case.execute.assert_called_once()
    assert mock_use_case.execute.call_args.kwargs["code"] == "PAC-2026-0029"
