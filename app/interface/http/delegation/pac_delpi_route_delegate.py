from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse, Response

from app.application.services.pac_api_delpi_delegation_service import (
    get_pac_api_delpi_delegation_service,
)


def delegate_json(
    *,
    method: str,
    path_suffix: str,
    pac_operation_id: str,
    query: dict[str, Any] | None = None,
    json_body: Any = None,
) -> JSONResponse:
    return get_pac_api_delpi_delegation_service().forward_json(
        method=method,
        path_suffix=path_suffix,
        pac_operation_id=pac_operation_id,
        query=query,
        json_body=json_body,
    )


def delegate_binary(
    *,
    method: str,
    path_suffix: str,
    pac_operation_id: str,
    query: dict[str, Any] | None = None,
) -> Response | JSONResponse:
    return get_pac_api_delpi_delegation_service().forward_binary(
        method=method,
        path_suffix=path_suffix,
        pac_operation_id=pac_operation_id,
        query=query,
    )


def delegate_multipart(
    *,
    path_suffix: str,
    pac_operation_id: str,
    form_data: dict[str, Any],
    file_field: str,
    file_name: str,
    file_content: bytes,
    file_content_type: str | None,
) -> JSONResponse:
    return get_pac_api_delpi_delegation_service().forward_multipart(
        path_suffix=path_suffix,
        pac_operation_id=pac_operation_id,
        form_data=form_data,
        file_field=file_field,
        file_name=file_name,
        file_content=file_content,
        file_content_type=file_content_type,
    )
