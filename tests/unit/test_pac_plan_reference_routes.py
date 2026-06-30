"""GET plano — referência por UUID ou código PAC (delegação api-delpi)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient


@pytest.fixture
def plans_client() -> TestClient:
    from app.interface.http.routes.quality_action_plans_router import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@patch("app.interface.http.routes.quality_action_plans_router.delegate_json")
def test_get_action_plan_by_code_returns_detail(
    mock_delegate: MagicMock,
    plans_client: TestClient,
) -> None:
    mock_delegate.return_value = JSONResponse(
        status_code=200,
        content={
            "success": True,
            "message": "ok",
            "data": {
                "plan": {"id": "uuid-1", "code": "PAC-2026-0029", "title": "Teste"},
                "ishikawa": None,
                "five_whys": None,
                "actions": [],
            },
        },
    )

    response = plans_client.get("/quality/action-plans/PAC-2026-0029")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    mock_delegate.assert_called_once()
    assert mock_delegate.call_args.kwargs["path_suffix"] == "/PAC-2026-0029"


@patch("app.interface.http.routes.quality_action_plans_router.delegate_json")
def test_get_action_plan_not_found_returns_404(
    mock_delegate: MagicMock,
    plans_client: TestClient,
) -> None:
    mock_delegate.return_value = JSONResponse(
        status_code=404,
        content={"success": False, "message": "Plano de ação não encontrado."},
    )

    response = plans_client.get("/quality/action-plans/PAC-2026-9999")
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False


@patch("app.interface.http.routes.quality_action_plans_router.delegate_json")
def test_list_action_plans_accepts_code_filter(
    mock_delegate: MagicMock,
    plans_client: TestClient,
) -> None:
    mock_delegate.return_value = JSONResponse(
        status_code=200,
        content={
            "success": True,
            "data": {
                "items": [{"id": "uuid-1", "code": "PAC-2026-0029"}],
                "pagination": {"page": 1, "page_size": 50, "total": 1, "total_pages": 1},
            },
        },
    )

    response = plans_client.get("/quality/action-plans", params={"code": "PAC-2026-0029"})
    assert response.status_code == 200
    mock_delegate.assert_called_once()
    assert mock_delegate.call_args.kwargs["query"]["code"] == "PAC-2026-0029"
