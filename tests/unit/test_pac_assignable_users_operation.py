from __future__ import annotations

from unittest.mock import patch

from app.interface.http.route_contract_registry import (
    ANALYST_PAC_OPERATION_IDS,
    CHATGPT_MAX_OPENAPI_OPERATIONS,
)


def test_assignable_users_in_analyst_openapi_budget():
    assert "pac_search_assignable_users" in ANALYST_PAC_OPERATION_IDS
    assert len(ANALYST_PAC_OPERATION_IDS) <= CHATGPT_MAX_OPENAPI_OPERATIONS
