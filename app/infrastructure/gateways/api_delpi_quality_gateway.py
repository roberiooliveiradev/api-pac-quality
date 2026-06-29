from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import settings
from app.infrastructure.http.delpi_service_auth import apply_internal_service_headers

logger = logging.getLogger(__name__)

_PAC_CALLER_APP = "api-pac-quality"
_PAC_ACTOR_ID = "pac-gpt-agent"
_PAC_ACTOR_NAME = "Agente GPT PAC"


class ApiDelpiQualityGatewayError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ApiDelpiQualityGateway:
    def __init__(self) -> None:
        self._base_url = (settings.API_DELPI_BASE_URL or "").rstrip("/")
        self._timeout = settings.API_DELPI_TIMEOUT_SECONDS

    @property
    def configured(self) -> bool:
        return bool(self._base_url and settings.API_DELPI_INTERNAL_SERVICE_TOKEN)

    def _url(self, path: str, query: dict[str, Any] | None = None) -> str:
        normalized = path if path.startswith("/") else f"/{path}"
        url = f"{self._base_url}{normalized}"
        if query:
            filtered = {k: v for k, v in query.items() if v is not None}
            if filtered:
                url = f"{url}?{urlencode(filtered, doseq=True)}"
        return url

    def _headers(self, *, content_type: str | None = "application/json") -> dict[str, str]:
        headers: dict[str, str] = {
            "Accept": "application/json, application/octet-stream, */*",
            "X-Delpi-Caller-App": _PAC_CALLER_APP,
            "X-Delpi-Actor-Id": _PAC_ACTOR_ID,
            "X-Delpi-Actor-Name": _PAC_ACTOR_NAME,
        }
        if content_type:
            headers["Content-Type"] = content_type
        apply_internal_service_headers(headers)
        return headers

    def request_json(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        json_body: Any = None,
    ) -> tuple[int, dict[str, str], Any]:
        if not self.configured:
            raise ApiDelpiQualityGatewayError("Gateway api-delpi não configurado.")

        url = self._url(path, query)
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.request(
                    method.upper(),
                    url,
                    headers=self._headers(),
                    json=json_body,
                )
        except httpx.RequestError as exc:
            logger.exception("Falha HTTP api-delpi %s %s", method, path)
            raise ApiDelpiQualityGatewayError(
                "api-delpi indisponível.",
                status_code=503,
            ) from exc

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                payload = response.json()
            except ValueError:
                payload = {"success": False, "message": response.text}
        else:
            payload = response.content

        return response.status_code, dict(response.headers), payload

    def request_binary(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        status, headers, payload = self.request_json(method, path, query=query)
        if isinstance(payload, bytes):
            return status, headers, payload
        raise ApiDelpiQualityGatewayError(
            "Resposta binária esperada da api-delpi.",
            status_code=status if status >= 400 else 502,
        )

    def request_multipart(
        self,
        path: str,
        *,
        form_data: dict[str, Any],
        file_field: str,
        file_name: str,
        file_content: bytes,
        file_content_type: str | None,
    ) -> tuple[int, dict[str, str], Any]:
        if not self.configured:
            raise ApiDelpiQualityGatewayError("Gateway api-delpi não configurado.")

        url = self._url(path)
        headers = self._headers(content_type=None)
        headers.pop("Content-Type", None)
        files = {
            file_field: (file_name, file_content, file_content_type or "application/octet-stream"),
        }
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    url,
                    headers=headers,
                    data=form_data,
                    files=files,
                )
        except httpx.RequestError as exc:
            logger.exception("Falha multipart api-delpi %s", path)
            raise ApiDelpiQualityGatewayError(
                "api-delpi indisponível.",
                status_code=503,
            ) from exc

        try:
            payload = response.json()
        except ValueError:
            payload = {"success": False, "message": response.text}
        return response.status_code, dict(response.headers), payload
