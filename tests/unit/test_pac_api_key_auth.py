"""Testes de autenticação por chave API (ChatGPT Actions)."""

from types import SimpleNamespace

import pytest

from app.interface.http.middleware.pac_api_key import request_has_valid_pac_api_key


class _FakeRequest:
    def __init__(self, headers: dict[str, str]):
        self.headers = headers


def test_request_has_valid_pac_api_key_bearer(monkeypatch):
    monkeypatch.setenv("PAC_QUALITY_API_KEY", "secret-token-123")
    request = _FakeRequest({"Authorization": "Bearer secret-token-123"})
    assert request_has_valid_pac_api_key(request) is True


def test_request_has_valid_pac_api_key_x_api_key(monkeypatch):
    monkeypatch.setenv("PAC_QUALITY_API_KEY", "secret-token-123")
    request = _FakeRequest({"X-Api-Key": "secret-token-123"})
    assert request_has_valid_pac_api_key(request) is True


def test_request_rejects_invalid_pac_api_key(monkeypatch):
    monkeypatch.setenv("PAC_QUALITY_API_KEY", "secret-token-123")
    request = _FakeRequest({"Authorization": "Bearer wrong"})
    assert request_has_valid_pac_api_key(request) is False


def test_request_without_configured_key(monkeypatch):
    monkeypatch.delenv("PAC_QUALITY_API_KEY", raising=False)
    request = _FakeRequest({"Authorization": "Bearer anything"})
    assert request_has_valid_pac_api_key(request) is False
