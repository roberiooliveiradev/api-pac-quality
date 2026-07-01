"""Injeta schemas de resposta no OpenAPI (rotas delegadas sem response_model)."""

from __future__ import annotations

from typing import Any

from app.interface.http.schemas.quality_action_plan_openapi import (
    ActionPlanDetailData,
    ActionPlanRow,
    PacEnvelopeSuccess,
    PlanContactRolesView,
    Rnc8dTemplatePayloadHeader,
    RNC8D_TEMPLATE_PAYLOAD_HEADER_KEYS,
)

# Ordem de registro: folhas antes dos compostos (refs em #/components/schemas/*).
_OPENAPI_DOCUMENTATION_MODELS: tuple[tuple[str, type], ...] = (
    ("PlanContactRolesView", PlanContactRolesView),
    ("Rnc8dTemplatePayloadHeader", Rnc8dTemplatePayloadHeader),
    ("ActionPlanRow", ActionPlanRow),
    ("ActionPlanDetailData", ActionPlanDetailData),
    ("PacActionPlanDetailEnvelope", PacEnvelopeSuccess),
)


def _flatten_schema_defs(schemas: dict[str, Any], name: str, body: dict[str, Any]) -> None:
    """Promove $defs para components.schemas — exigido pelo importador OpenAPI do ChatGPT."""
    defs = body.get("$defs")
    if isinstance(defs, dict):
        for def_name, def_body in defs.items():
            if def_name in schemas or not isinstance(def_body, dict):
                continue
            _flatten_schema_defs(schemas, def_name, def_body)

    cleaned = {key: value for key, value in body.items() if key != "$defs"}
    schemas[name] = cleaned


def _register_schema(openapi_schema: dict[str, Any], name: str, model: type) -> None:
    components = openapi_schema.setdefault("components", {})
    schemas = components.setdefault("schemas", {})
    raw = model.model_json_schema(ref_template="#/components/schemas/{model}")
    _flatten_schema_defs(schemas, name, raw)


def inject_pac_response_schemas(openapi_schema: dict[str, Any]) -> dict[str, int]:
    for schema_name, model in _OPENAPI_DOCUMENTATION_MODELS:
        _register_schema(openapi_schema, schema_name, model)

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
            if isinstance(schema, dict):
                props = schema.get("properties")
                if not isinstance(props, dict) and schema.get("$ref", "").endswith("Rnc8dReportBody"):
                    props = schema.setdefault("properties", {})
                if isinstance(props, dict) and "template_payload" in props:
                    props["template_payload"] = {
                        "$ref": "#/components/schemas/Rnc8dTemplatePayloadHeader",
                        "description": (
                            "Cabeçalho material/NF e demais seções 8D. "
                            f"Chaves do cabeçalho: {', '.join(RNC8D_TEMPLATE_PAYLOAD_HEADER_KEYS)}."
                        ),
                    }
                    injected += 1

    return {"responseSchemas": injected}
