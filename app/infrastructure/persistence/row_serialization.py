from __future__ import annotations

from datetime import datetime
from typing import Any


def serialize_row(
    row: dict[str, Any] | None,
    *,
    id_keys: tuple[str, ...] = ("id",),
) -> dict[str, Any] | None:
    if row is None:
        return None
    result = dict(row)
    for key in id_keys:
        if result.get(key) is not None:
            result[key] = str(result[key])
    for key, value in list(result.items()):
        if isinstance(value, datetime):
            result[key] = value.isoformat()
    return result


def serialize_plan_row(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    if result.get("id") is not None:
        result["id"] = str(result["id"])
    for key in (
        "detected_at",
        "reported_at",
        "effectiveness_verified_at",
        "effectiveness_submitted_at",
        "effectiveness_reviewed_at",
        "created_at",
        "updated_at",
        "closed_at",
    ):
        value = result.get(key)
        if isinstance(value, datetime):
            result[key] = value.isoformat()
    tags = result.get("symptom_tags")
    if tags is None:
        result["symptom_tags"] = []
    if result.get("template_payload") is None:
        result["template_payload"] = {}
    return result
