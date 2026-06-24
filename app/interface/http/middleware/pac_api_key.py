from __future__ import annotations

import os
import secrets
from typing import Final

PAC_QUALITY_API_KEY_ENV: Final[str] = "PAC_QUALITY_API_KEY"


def get_pac_quality_api_key() -> str | None:
    value = (os.getenv(PAC_QUALITY_API_KEY_ENV) or "").strip()
    return value or None


def request_has_valid_pac_api_key(request) -> bool:
    expected = get_pac_quality_api_key()
    if not expected:
        return False

    authorization = (request.headers.get("Authorization") or "").strip()
    if authorization.startswith("Bearer "):
        provided = authorization[7:].strip()
        if provided and secrets.compare_digest(provided, expected):
            return True

    header_key = (request.headers.get("X-Api-Key") or "").strip()
    if header_key and secrets.compare_digest(header_key, expected):
        return True

    return False
