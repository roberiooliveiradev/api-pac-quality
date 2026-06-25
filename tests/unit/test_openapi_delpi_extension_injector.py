"""x-delpi no OpenAPI — Playbook 22 Fase 13."""

from app.interface.http.openapi_delpi_extension_injector import (
    build_x_delpi_extension,
    inject_delpi_extensions,
)


def test_build_x_delpi_extension_from_route_contract():
    extension = build_x_delpi_extension("pac_list_action_plans")

    assert extension == {
        "entity": "quality_action_plan",
        "shape": "paged_list",
        "presentation": {"strategy": "as_delivered"},
    }


def test_inject_delpi_extensions_skips_health():
    schema = {
        "paths": {
            "/health": {
                "get": {
                    "operationId": "health_health_get",
                    "summary": "Health",
                }
            },
            "/quality/action-plans": {
                "get": {
                    "operationId": "pac_list_action_plans",
                    "summary": "Listar planos",
                }
            },
        }
    }

    stats = inject_delpi_extensions(schema)

    assert stats == {
        "operations": 1,
        "withDelpiExtension": 1,
        "skippedWithoutOperationId": 0,
    }
    assert "x-delpi" not in schema["paths"]["/health"]["get"]
    assert schema["paths"]["/quality/action-plans"]["get"]["x-delpi"]["entity"] == "quality_action_plan"


def test_openapi_schema_exposes_x_delpi_for_pac_routes():
    from app.interface.http.route_contract_registry import ROUTE_CONTRACTS

    schema = {
        "paths": {
            "/quality/action-plans": {
                "get": {"operationId": "pac_list_action_plans"},
            },
            "/quality/action-plans/intelligence/similar-cases": {
                "post": {"operationId": "pac_search_similar_cases"},
            },
        }
    }

    inject_delpi_extensions(schema)
    missing: list[str] = []

    for path_item in schema.get("paths", {}).values():
        if not isinstance(path_item, dict):
            continue

        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue

            operation_id = str(operation.get("operationId") or "").strip()
            extension = operation.get("x-delpi")

            if (
                not isinstance(extension, dict)
                or not extension.get("entity")
                or not extension.get("shape")
            ):
                missing.append(operation_id)

    assert not missing
    assert len(ROUTE_CONTRACTS) >= 18


def test_all_published_openapi_operations_have_x_delpi_matching_registry():
    from app.interface.http.route_contract_registry import ROUTE_CONTRACTS

    schema = {"paths": {}}

    for operation_id in ROUTE_CONTRACTS:
        schema["paths"][f"/mock/{operation_id}"] = {
            "get": {"operationId": operation_id},
        }

    inject_delpi_extensions(schema)
    mismatches: list[str] = []

    for path_item in schema.get("paths", {}).values():
        if not isinstance(path_item, dict):
            continue

        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue

            operation_id = str(operation.get("operationId") or "").strip()
            extension = operation.get("x-delpi")

            if not isinstance(extension, dict):
                mismatches.append(operation_id)
                continue

            contract = ROUTE_CONTRACTS.get(operation_id)

            if contract is None:
                continue

            if extension.get("entity") != contract.entity or extension.get("shape") != contract.shape:
                mismatches.append(operation_id)

            presentation = extension.get("presentation") or {}

            if presentation.get("strategy") != "as_delivered":
                mismatches.append(operation_id)

    assert not mismatches
