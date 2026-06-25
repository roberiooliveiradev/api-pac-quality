"""Injeta extensão x-delpi no OpenAPI a partir de route_contract_registry — Playbook 22."""

from __future__ import annotations

from typing import Any

from app.interface.http.route_contract_registry import ROUTE_CONTRACTS, resolve_contract

HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete", "head", "options"})
SKIP_PATH_PREFIXES = ("/health",)


def build_x_delpi_extension(operation_id: str) -> dict[str, Any]:
    contract = ROUTE_CONTRACTS.get(str(operation_id or "").strip())

    if contract is not None:
        entity, shape = contract.entity, contract.shape
    else:
        entity, shape = resolve_contract(operation_id)

    return {
        "entity": entity,
        "shape": shape,
        "presentation": {"strategy": "as_delivered"},
    }


def inject_delpi_extensions(openapi_schema: dict[str, Any]) -> dict[str, int]:
    paths = openapi_schema.get("paths")

    if not isinstance(paths, dict):
        return {"operations": 0, "withDelpiExtension": 0, "skippedWithoutOperationId": 0}

    operations = 0
    with_extension = 0
    skipped = 0

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue

        path_token = str(path or "").strip()

        if any(path_token.startswith(prefix) for prefix in SKIP_PATH_PREFIXES):
            continue

        for method, operation in path_item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                continue

            operations += 1
            operation_id = str(operation.get("operationId") or "").strip()

            if not operation_id:
                skipped += 1
                continue

            operation["x-delpi"] = build_x_delpi_extension(operation_id)
            with_extension += 1

    return {
        "operations": operations,
        "withDelpiExtension": with_extension,
        "skippedWithoutOperationId": skipped,
    }
