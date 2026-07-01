"""Injeta schemas de resposta no OpenAPI (rotas delegadas sem response_model)."""

from __future__ import annotations

from typing import Any

from app.interface.http.schemas.quality_action_plan_openapi import (
    ActionPlanDetailData,
    PacEnvelopeSuccess,
    PlanContactRolesView,
    Rnc8dTemplatePayloadHeader,
    RNC8D_TEMPLATE_PAYLOAD_HEADER_KEYS,
)


def _register_schema(openapi_schema: dict[str, Any], name: str, model: type) -> None:
    components = openapi_schema.setdefault("components", {})
    schemas = components.setdefault("schemas", {})
    schemas[name] = model.model_json_schema(ref_template="#/components/schemas/{model}")


def inject_pac_response_schemas(openapi_schema: dict[str, Any]) -> dict[str, int]:
    _register_schema(openapi_schema, "PlanContactRolesView", PlanContactRolesView)
    _register_schema(openapi_schema, "Rnc8dTemplatePayloadHeader", Rnc8dTemplatePayloadHeader)
    _register_schema(openapi_schema, "ActionPlanDetailData", ActionPlanDetailData)
    _register_schema(openapi_schema, "PacActionPlanDetailEnvelope", PacEnvelopeSuccess)

    paths = openapi_schema.get("paths")
    if not isinstance(paths, dict):
        return {"responseSchemas": 0}

    injected = 0
    detail_path = paths.get("/quality/action-plans/{plan_id}")
    if isinstance(detail_path, dict):
        get_op = detail_path.get("get")
        if isinstance(get_op, dict):
            responses = get_op.setdefault("responses", {})
            responses["200"] = {
                "description": "Detalhe do plano (delegado api-delpi).",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/PacActionPlanDetailEnvelope"},
                    },
                },
            }
            injected += 1

    rnc_path = paths.get("/quality/action-plans/{plan_id}/rnc-8d")
    if isinstance(rnc_path, dict):
        put_op = rnc_path.get("put")
        if isinstance(put_op, dict):
            request_body = put_op.setdefault("requestBody", {})
            content = request_body.setdefault("content", {})
            json_body = content.setdefault("application/json", {})
            schema = json_body.get("schema")
            if isinstance(schema, dict) and schema.get("$ref", "").endswith("Rnc8dReportBody"):
                props = schema.setdefault("properties", {})
                payload = props.setdefault("template_payload", {})
                if isinstance(payload, dict):
                    payload["$ref"] = "#/components/schemas/Rnc8dTemplatePayloadHeader"
                    payload["description"] = (
                        "Cabeçalho material/NF e demais seções 8D. "
                        f"Chaves do cabeçalho: {', '.join(RNC8D_TEMPLATE_PAYLOAD_HEADER_KEYS)}."
                    )
                injected += 1

    return {"responseSchemas": injected}
