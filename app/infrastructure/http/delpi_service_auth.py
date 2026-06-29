from __future__ import annotations

import os


def get_internal_service_token() -> str | None:
    token = (os.getenv("API_DELPI_INTERNAL_SERVICE_TOKEN") or "").strip()
    return token or None


def apply_internal_service_headers(headers: dict[str, str]) -> None:
    token = get_internal_service_token()
    if not token:
        return
    headers["X-Delpi-Service-Token"] = token
    if "Authorization" not in headers:
        bearer = token if token.startswith("Bearer ") else f"Bearer {token}"
        headers["Authorization"] = bearer
