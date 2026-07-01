"""Paridade de contrato (campos) api-delpi ↔ api-pac-quality — planos de ação."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from app.interface.http.routes.quality_action_plans_router import (
    CreateActionPlanBody,
    UpdateActionPlanBody,
)

# Campos expostos na api-delpi (action_plans_read_router) após V018.
DELPI_CREATE_PLAN_FIELDS = {
    "title",
    "customer_name",
    "customer_code",
    "customer_store",
    "customer_contact",
    "customer_contact_email",
    "customer_contact_phone",
    "delpi_contact_name",
    "delpi_contact_area",
    "delpi_sales_rep",
    "delpi_quality_contact",
    "source_type",
    "source_reference",
    "product_code",
    "product_description",
    "batch_number",
    "reported_problem",
    "detected_at",
    "reported_at",
    "severity",
    "status",
    "owner_user_id",
    "branch_code",
    "nonconformity_scope",
    "department",
    "problem_category",
    "symptom_tags",
    "root_cause_category",
    "failure_mode",
    "recurrence_key",
    "customer_template",
    "client_nc_registry",
}

DELPI_UPDATE_PLAN_FIELDS = {
    field for field in DELPI_CREATE_PLAN_FIELDS if field not in {"status"}
}


def _model_fields(model: type[BaseModel]) -> set[str]:
    return set(model.model_fields.keys())


def test_create_body_has_all_delpi_fields() -> None:
    missing = sorted(DELPI_CREATE_PLAN_FIELDS - _model_fields(CreateActionPlanBody))
    assert not missing, f"CreateActionPlanBody sem campos da api-delpi: {missing}"


def test_update_body_has_all_delpi_fields() -> None:
    missing = sorted(DELPI_UPDATE_PLAN_FIELDS - _model_fields(UpdateActionPlanBody))
    assert not missing, f"UpdateActionPlanBody sem campos da api-delpi: {missing}"


def test_create_body_rejects_free_text_in_detected_at() -> None:
    with pytest.raises(ValueError, match="detected_at"):
        CreateActionPlanBody(
            title="NC teste",
            branch_code="01",
            nonconformity_scope="external",
            detected_at="Produção do cliente",
        )
