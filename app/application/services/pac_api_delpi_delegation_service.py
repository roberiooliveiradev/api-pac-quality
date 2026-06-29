from __future__ import annotations

import logging
from typing import Any

from fastapi.responses import JSONResponse, Response

from app.config import settings
from app.domain.services.pac_delpi_operation_mapping import (
    DELPI_TO_PAC_OPERATION_ID,
    PAC_TRANSACTIONAL_PREFIX,
)
from app.infrastructure.gateways.api_delpi_quality_gateway import (
    ApiDelpiQualityGateway,
    ApiDelpiQualityGatewayError,
)

logger = logging.getLogger(__name__)


class PacApiDelpiDelegationService:
    def __init__(self, gateway: ApiDelpiQualityGateway | None = None) -> None:
        self._gateway = gateway or ApiDelpiQualityGateway()

    def enabled(self) -> bool:
        if not settings.PAC_DELEGATE_TRANSACTIONAL_TO_API_DELPI:
            return False
        return self._gateway.configured

    def _rewrite_meta(self, payload: dict[str, Any], pac_operation_id: str) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return payload
        meta = payload.get("meta")
        if isinstance(meta, dict):
            delpi_op = meta.get("operationId")
            if isinstance(delpi_op, str) and delpi_op in DELPI_TO_PAC_OPERATION_ID:
                meta = {**meta, "operationId": DELPI_TO_PAC_OPERATION_ID[delpi_op]}
            else:
                meta = {**meta, "operationId": pac_operation_id}
            payload = {**payload, "meta": meta}
        return payload

    def _json_response(
        self,
        status_code: int,
        payload: Any,
        *,
        pac_operation_id: str,
    ) -> JSONResponse:
        if isinstance(payload, dict):
            payload = self._rewrite_meta(payload, pac_operation_id)
        return JSONResponse(status_code=status_code, content=payload)

    def _path(self, suffix: str) -> str:
        if not suffix:
            return PAC_TRANSACTIONAL_PREFIX
        if suffix.startswith("/"):
            return f"{PAC_TRANSACTIONAL_PREFIX}{suffix}"
        return f"{PAC_TRANSACTIONAL_PREFIX}/{suffix}"

    def forward_json(
        self,
        *,
        method: str,
        path_suffix: str,
        pac_operation_id: str,
        query: dict[str, Any] | None = None,
        json_body: Any = None,
    ) -> JSONResponse | None:
        if not self.enabled():
            return None
        try:
            status, _headers, payload = self._gateway.request_json(
                method,
                self._path(path_suffix),
                query=query,
                json_body=json_body,
            )
        except ApiDelpiQualityGatewayError as exc:
            code = exc.status_code or 503
            return JSONResponse(
                status_code=code,
                content={
                    "success": False,
                    "message": str(exc),
                    "data": None,
                    "error": {"code": "API_DELPI_UNAVAILABLE", "recoverable": True},
                },
            )
        if isinstance(payload, dict):
            return self._json_response(status, payload, pac_operation_id=pac_operation_id)
        return JSONResponse(
            status_code=502,
            content={
                "success": False,
                "message": "Resposta inválida da api-delpi.",
                "data": None,
                "error": {"code": "API_DELPI_BAD_RESPONSE", "recoverable": True},
            },
        )

    def forward_binary(
        self,
        *,
        method: str,
        path_suffix: str,
        pac_operation_id: str,
        query: dict[str, Any] | None = None,
    ) -> Response | JSONResponse | None:
        if not self.enabled():
            return None
        try:
            status, headers, payload = self._gateway.request_json(
                method,
                self._path(path_suffix),
                query=query,
            )
        except ApiDelpiQualityGatewayError as exc:
            code = exc.status_code or 503
            return JSONResponse(
                status_code=code,
                content={
                    "success": False,
                    "message": str(exc),
                    "data": None,
                    "error": {"code": "API_DELPI_UNAVAILABLE", "recoverable": True},
                },
            )
        if isinstance(payload, dict):
            return self._json_response(status, payload, pac_operation_id=pac_operation_id)
        if not isinstance(payload, bytes):
            return JSONResponse(
                status_code=502,
                content={"success": False, "message": "Resposta binária inválida."},
            )
        response_headers: dict[str, str] = {}
        for key in ("content-type", "content-disposition"):
            if key in headers:
                response_headers[key.title()] = headers[key]
        return Response(content=payload, status_code=status, headers=response_headers)

    def forward_multipart(
        self,
        *,
        path_suffix: str,
        pac_operation_id: str,
        form_data: dict[str, Any],
        file_field: str,
        file_name: str,
        file_content: bytes,
        file_content_type: str | None,
    ) -> JSONResponse | None:
        if not self.enabled():
            return None
        try:
            status, _headers, payload = self._gateway.request_multipart(
                self._path(path_suffix),
                form_data=form_data,
                file_field=file_field,
                file_name=file_name,
                file_content=file_content,
                file_content_type=file_content_type,
            )
        except ApiDelpiQualityGatewayError as exc:
            code = exc.status_code or 503
            return JSONResponse(
                status_code=code,
                content={
                    "success": False,
                    "message": str(exc),
                    "data": None,
                    "error": {"code": "API_DELPI_UNAVAILABLE", "recoverable": True},
                },
            )
        if isinstance(payload, dict):
            return self._json_response(status, payload, pac_operation_id=pac_operation_id)
        return JSONResponse(
            status_code=502,
            content={"success": False, "message": "Resposta inválida da api-delpi."},
        )


_delegation_service: PacApiDelpiDelegationService | None = None


def get_pac_api_delpi_delegation_service() -> PacApiDelpiDelegationService:
    global _delegation_service
    if _delegation_service is None:
        _delegation_service = PacApiDelpiDelegationService()
    return _delegation_service
