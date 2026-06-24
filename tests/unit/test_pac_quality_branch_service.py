import pytest

from app.domain.services.pac_quality_branch_service import (
    build_recurrence_key,
    normalize_branch_code,
    validate_branch_code,
)


def test_normalize_branch_code_pads_single_digit():
    assert normalize_branch_code("1") == "01"
    assert normalize_branch_code("02") == "02"


def test_validate_branch_code_required():
    with pytest.raises(ValueError, match="branch_code é obrigatório"):
        validate_branch_code(None, required=True)


def test_validate_branch_code_rejects_invalid():
    with pytest.raises(ValueError, match="branch_code inválido"):
        validate_branch_code("99")


def test_build_recurrence_key_prefers_explicit():
    assert build_recurrence_key(
        branch_code="01",
        product_code="010101",
        failure_mode="rompimento",
        explicit="custom-key",
    ) == "custom-key"


def test_build_recurrence_key_composes_parts():
    assert build_recurrence_key(
        branch_code="02",
        product_code="010101",
        failure_mode="rompimento",
        explicit=None,
    ) == "filial:02|produto:010101|falha:rompimento"
