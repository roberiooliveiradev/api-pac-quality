"""OpenAPI — schemas de resposta do detalhe do plano e cabeçalho 8D."""

from __future__ import annotations

from app.interface.http.openapi_response_schema_injector import inject_pac_response_schemas
from app.interface.http.openapi_schema import build_openapi_schema
from app.interface.http.schemas.quality_action_plan_openapi import RNC8D_TEMPLATE_PAYLOAD_HEADER_KEYS
from app.main import app


def test_openapi_get_action_plan_documents_detail_envelope():
    schema = build_openapi_schema(app)
    get_op = schema["paths"]["/quality/action-plans/{plan_id}"]["get"]
    response_schema = (
        get_op["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    )
    assert response_schema == "#/components/schemas/PacActionPlanDetailEnvelope"

    components = schema["components"]["schemas"]
    assert "PlanContactRolesView" in components
    assert "Rnc8dTemplatePayloadHeader" in components
    assert "ActionPlanRow" in components
    assert components["ActionPlanRow"]["type"] == "object"
    assert "$defs" not in components["ActionPlanDetailData"]
    assert "$defs" not in components["PacActionPlanDetailEnvelope"]
    plan_props = components["ActionPlanDetailData"]["properties"]["plan"]
    assert plan_props["$ref"] == "#/components/schemas/ActionPlanRow"


def test_rnc8d_template_payload_header_keys_match_plugin_material_section():
    expected = {
        "contact_phone",
        "purchase_order",
        "invoice_number",
        "invoice_date",
        "defective_quantity",
        "client_batch",
        "batch_quantity",
        "disposition",
        "rejected_quantity",
        "return_by",
    }
    documented = {key for key in RNC8D_TEMPLATE_PAYLOAD_HEADER_KEYS if key not in {"attention_to", "attention_email"}}
    assert expected <= documented


def test_inject_pac_response_schemas_idempotent():
    schema = build_openapi_schema(app)
    stats = inject_pac_response_schemas(schema)
    assert stats["responseSchemas"] >= 1
