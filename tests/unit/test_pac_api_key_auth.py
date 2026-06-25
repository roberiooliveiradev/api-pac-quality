"""Autenticação PAC — somente PAC_QUALITY_API_KEY (sem delpi_auth / JWT)."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.interface.http.middleware.pac_auth_middleware import pac_auth_middleware


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.middleware("http")(pac_auth_middleware)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/quality/action-plans")
    def list_plans():
        return {"success": True}

    return app


def test_public_health_without_api_key():
    client = TestClient(_build_test_app())
    response = client.get("/health")
    assert response.status_code == 200


def test_protected_route_requires_api_key():
    client = TestClient(_build_test_app())
    response = client.get("/quality/action-plans")
    assert response.status_code == 401
    assert response.json()["success"] is False


def test_protected_route_accepts_bearer_api_key():
    with patch.dict(os.environ, {"PAC_QUALITY_API_KEY": "test-pac-key"}, clear=False):
        client = TestClient(_build_test_app())
        response = client.get(
            "/quality/action-plans",
            headers={"Authorization": "Bearer test-pac-key"},
        )
        assert response.status_code == 200


def test_protected_route_accepts_x_api_key_header():
    with patch.dict(os.environ, {"PAC_QUALITY_API_KEY": "test-pac-key"}, clear=False):
        client = TestClient(_build_test_app())
        response = client.get(
            "/quality/action-plans",
            headers={"X-Api-Key": "test-pac-key"},
        )
        assert response.status_code == 200
