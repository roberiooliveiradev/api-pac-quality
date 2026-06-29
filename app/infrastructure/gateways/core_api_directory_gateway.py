"""Busca usuários elegíveis para responsável de ação PAC (core-api S2S)."""

from __future__ import annotations

import logging
from urllib.parse import urlencode

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_PAC_QUALITY_APP_ID = "quality-action-plans"


class CoreApiDirectoryGatewayError(Exception):
    pass


class CoreApiDirectoryGateway:
    def configured(self) -> bool:
        return bool(
            (settings.CORE_API_BASE_URL or "").strip()
            and (settings.CORE_API_INTEGRATIONS_SERVICE_TOKEN or "").strip()
        )

    def search_assignable_users(
        self,
        *,
        query: str,
        limit: int = 10,
    ) -> list[dict]:
        if not self.configured():
            raise CoreApiDirectoryGatewayError("Core API não configurada para diretório.")

        base_url = (settings.CORE_API_BASE_URL or "").rstrip("/")
        token = (settings.CORE_API_INTEGRATIONS_SERVICE_TOKEN or "").strip()
        params = urlencode(
            {
                "q": query.strip(),
                "limit": max(1, min(limit, 20)),
                "app": _PAC_QUALITY_APP_ID,
            }
        )
        url = f"{base_url}/integrations/directory/users?{params}"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Delpi-Service-Token": token,
            "Accept": "application/json",
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, headers=headers)
        except httpx.RequestError as exc:
            logger.exception("Falha ao buscar diretório core-api")
            raise CoreApiDirectoryGatewayError("Core API indisponível.") from exc

        if response.status_code >= 400:
            raise CoreApiDirectoryGatewayError(
                f"Core API rejeitou busca de usuários (HTTP {response.status_code})."
            )

        payload = response.json()
        items = payload.get("items") if isinstance(payload, dict) else None
        return items if isinstance(items, list) else []
