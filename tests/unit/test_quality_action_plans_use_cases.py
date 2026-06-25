from unittest.mock import MagicMock

import pytest

from app.application.use_cases.quality_action_plans_use_cases import (
    CreateQualityActionPlanRequest,
    CreateQualityActionPlanUseCase,
    UpdateQualityActionPlanStatusUseCase,
)


def test_create_plan_requires_branch_code():
    repository = MagicMock()
    use_case = CreateQualityActionPlanUseCase(repository)

    with pytest.raises(ValueError, match="branch_code"):
        use_case.execute(
            CreateQualityActionPlanRequest(
                title="Falha no cabo",
                created_by_user_id="user-1",
            )
        )

    repository.create_plan.assert_not_called()


def test_create_plan_requires_non_empty_title():
    repository = MagicMock()
    use_case = CreateQualityActionPlanUseCase(repository)

    with pytest.raises(ValueError, match="title"):
        use_case.execute(
            CreateQualityActionPlanRequest(
                title="   ",
                created_by_user_id="user-1",
            )
        )

    repository.create_plan.assert_not_called()


def test_create_plan_delegates_to_repository():
    repository = MagicMock()
    repository.create_plan.return_value = {"id": "uuid", "code": "PAC-2026-0001"}
    use_case = CreateQualityActionPlanUseCase(repository)

    result = use_case.execute(
        CreateQualityActionPlanRequest(
            title="Falha no cabo",
            created_by_user_id="user-1",
            product_code="010101",
            branch_code="01",
            nonconformity_scope="external",
        )
    )

    assert result["code"] == "PAC-2026-0001"
    repository.create_plan.assert_called_once()
    payload = repository.create_plan.call_args.args[0]
    assert payload["title"] == "Falha no cabo"
    assert payload["product_code"] == "010101"
    assert payload["branch_code"] == "01"
    assert payload["recurrence_key"] == "filial:01|produto:010101"


def test_update_status_rejects_invalid_status():
    repository = MagicMock()
    use_case = UpdateQualityActionPlanStatusUseCase(repository)

    with pytest.raises(ValueError, match="status inválido"):
        use_case.execute("plan-id", status="invalid", updated_by="user-1")
