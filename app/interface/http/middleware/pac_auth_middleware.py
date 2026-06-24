from __future__ import annotations

import logging
from types import SimpleNamespace

from fastapi import Request
from fastapi.responses import JSONResponse

from delpi_auth.middleware.fastapi_auth import is_public_path, jwt_middleware
from delpi_auth.request_context import (
    clear_current_user,
    clear_request_authorization,
    reset_current_user,
    reset_request_authorization,
    set_current_user,
    set_request_authorization,
)

from app.interface.http.middleware.pac_api_key import request_has_valid_pac_api_key

logger = logging.getLogger(__name__)

_PAC_GPT_AGENT_USER = SimpleNamespace(
    id="pac-gpt-agent",
    email="pac-gpt-agent@delpi.internal",
    name="Agente GPT PAC",
    roles=["pac-api-key"],
    groups=[],
    permissions=[],
    is_superadmin=True,
    access_token=None,
)


async def pac_auth_middleware(request: Request, call_next):
    """Aceita PAC_QUALITY_API_KEY (ChatGPT Actions) ou JWT Keycloak (Minha DELPI)."""
    clear_current_user()
    clear_request_authorization()

    path = request.url.path
    if is_public_path(path):
        return await call_next(request)

    if request_has_valid_pac_api_key(request):
        request.state.user = _PAC_GPT_AGENT_USER
        context_token = set_current_user(_PAC_GPT_AGENT_USER)
        auth_context_token = set_request_authorization("Bearer [pac-api-key]")
        try:
            return await call_next(request)
        except Exception:
            logger.exception("unhandled_error_pac_api_key_request path=%s", path)
            return JSONResponse(status_code=500, content={"detail": "Internal server error"})
        finally:
            reset_request_authorization(auth_context_token)
            reset_current_user(context_token)

    return await jwt_middleware(request, call_next)
