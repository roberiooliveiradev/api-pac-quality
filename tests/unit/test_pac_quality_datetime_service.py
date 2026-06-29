from __future__ import annotations

import pytest

from app.domain.services.pac_quality_datetime_service import validate_optional_iso_datetime


def test_validate_optional_iso_datetime_accepts_iso() -> None:
    assert validate_optional_iso_datetime("2026-06-24T10:00:00-03:00", field_name="detected_at")


def test_validate_optional_iso_datetime_rejects_free_text() -> None:
    with pytest.raises(ValueError, match="detected_at"):
        validate_optional_iso_datetime("Produção do cliente", field_name="detected_at")
