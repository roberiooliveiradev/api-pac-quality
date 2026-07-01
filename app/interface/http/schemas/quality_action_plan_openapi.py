"""Schemas OpenAPI — detalhe do plano e cabeçalho 8D (documentação GPT)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PlanContactRolesView(BaseModel):
    """Papéis de contato resolvidos (leitura / export 8D)."""

    customer_contact: str | None = None
    customer_contact_email: str | None = None
    customer_contact_phone: str | None = None
    delpi_contact_name: str | None = None
    delpi_contact_area: str | None = None
    delpi_contact_area_label: str | None = None
    delpi_sales_rep: str | None = None
    delpi_quality_contact: str | None = None
    delpi_contact_phone: str | None = Field(
        default=None,
        description="Telefone DELPI (espelho de template_payload.contact_phone).",
    )


class Rnc8dTemplatePayloadHeader(BaseModel):
    """Cabeçalho «Material e nota fiscal» — gravar em pac_upsert_rnc_8d → template_payload."""

    model_config = ConfigDict(extra="allow")

    contact_phone: str | None = Field(default=None, description="Telefone DELPI (comercial).")
    purchase_order: str | None = Field(default=None, description="Ordem de compra / posição.")
    invoice_number: str | None = Field(default=None, description="Número da nota fiscal.")
    invoice_date: str | None = Field(default=None, description="Data digitação NF (ISO ou texto).")
    defective_quantity: str | None = Field(default=None, description="Quantidade defeituosa.")
    client_batch: str | None = Field(default=None, description="Lote do cliente.")
    batch_quantity: str | None = Field(default=None, description="Quantidade do lote.")
    disposition: str | None = Field(default=None, description="Disposição do material.")
    rejected_quantity: str | None = Field(default=None, description="Quantidade rejeitada.")
    return_by: str | None = Field(default=None, description="Devolver relatório até.")
    attention_to: str | None = Field(
        default=None,
        description="Legado — sincroniza com customer_contact; preferir colunas do plano.",
    )
    attention_email: str | None = Field(
        default=None,
        description="Legado — sincroniza com customer_contact_email.",
    )


class ActionPlanRow(BaseModel):
    """Plano no detalhe (pac_get_action_plan → data.plan)."""

    model_config = ConfigDict(extra="allow")

    id: str
    code: str | None = None
    title: str | None = None
    customer_name: str | None = None
    customer_code: str | None = None
    customer_store: str | None = None
    customer_contact: str | None = Field(default=None, description="Contato no cliente (destinatário 8D).")
    customer_contact_email: str | None = None
    customer_contact_phone: str | None = None
    delpi_contact_name: str | None = Field(default=None, description="Interlocutor DELPI no caso.")
    delpi_contact_area: str | None = Field(
        default=None,
        description="comercial | qualidade | pcp | engenharia | outro",
    )
    delpi_sales_rep: str | None = None
    delpi_quality_contact: str | None = None
    client_nc_registry: str | None = None
    export_template_key: str | None = Field(
        default=None,
        description="Modelo Excel 8D preferido (weg_wfr20997, delpi_8d).",
    )
    template_payload: Rnc8dTemplatePayloadHeader | dict[str, Any] = Field(
        default_factory=dict,
        description="Seções 8D; cabeçalho material/NF nas chaves documentadas em Rnc8dTemplatePayloadHeader.",
    )
    contact_roles: PlanContactRolesView | None = Field(
        default=None,
        description="Visão resolvida cliente vs DELPI — preferir na leitura.",
    )
    product_code: str | None = None
    product_description: str | None = None
    batch_number: str | None = None
    reported_problem: str | None = None
    branch_code: str | None = None
    nonconformity_scope: str | None = None
    status: str | None = None
    severity: str | None = None


class ActionPlanDetailData(BaseModel):
    """Corpo data de pac_get_action_plan (detail=true)."""

    model_config = ConfigDict(extra="allow")

    plan: ActionPlanRow
    ishikawa: dict[str, Any] | None = None
    five_whys: dict[str, Any] | None = None
    actions: list[dict[str, Any]] = Field(default_factory=list)
    team_members: list[dict[str, Any]] = Field(default_factory=list)
    evidences: list[dict[str, Any]] = Field(default_factory=list)
    history: list[dict[str, Any]] = Field(default_factory=list)


class PacEnvelopeSuccess(BaseModel):
    success: bool = True
    message: str = "Operação realizada com sucesso"
    data: ActionPlanDetailData | dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None


RNC8D_TEMPLATE_PAYLOAD_HEADER_KEYS = tuple(Rnc8dTemplatePayloadHeader.model_fields.keys())
