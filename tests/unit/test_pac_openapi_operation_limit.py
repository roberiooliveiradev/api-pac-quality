"""OpenAPI api-pac-quality — fluxo analista GPT (≤30 operações ChatGPT)."""

from __future__ import annotations

from app.interface.http.openapi_schema import build_openapi_schema
from app.interface.http.route_contract_registry import (
    ANALYST_PAC_OPERATION_IDS,
    CHATGPT_MAX_OPENAPI_OPERATIONS,
    ROUTE_CONTRACTS,
)
from app.main import app


def _iter_openapi_operation_ids(schema: dict) -> set[str]:
    operation_ids: set[str] = set()
    paths = schema.get("paths")

    if not isinstance(paths, dict):
        return operation_ids

    for path_item in paths.values():
        if not isinstance(path_item, dict):
            continue

        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue

            operation_id = str(operation.get("operationId") or "").strip()

            if operation_id:
                operation_ids.add(operation_id)

    return operation_ids


def test_route_registry_matches_analyst_operation_set():
    assert frozenset(ROUTE_CONTRACTS) == ANALYST_PAC_OPERATION_IDS


def test_openapi_exposes_only_analyst_operations():
    schema = build_openapi_schema(app)
    published = _iter_openapi_operation_ids(schema)

    assert published == ANALYST_PAC_OPERATION_IDS
    assert len(published) == 26
    assert len(published) <= CHATGPT_MAX_OPENAPI_OPERATIONS
    assert "/health" not in schema.get("paths", {})
