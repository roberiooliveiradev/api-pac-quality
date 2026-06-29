from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.core.responses import error_response, not_found_response
from app.interface.http.openapi_schema import build_openapi_schema
from app.interface.http.middleware.pac_auth_middleware import pac_auth_middleware
from app.interface.http.routes.quality_intelligence_router import router as intelligence_router
from app.interface.http.routes.quality_action_plans_router import router as action_plans_router
from app.application.services.pac_api_delpi_delegation_service import (
    get_pac_api_delpi_delegation_service,
)
from app.infrastructure.gateways.core_api_directory_gateway import CoreApiDirectoryGateway
from app.infrastructure.providers.database.plugins_postgres_connection import check_plugins_connection

logger = logging.getLogger(__name__)

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))


def build_allowed_origins() -> list[str]:
    origins: set[str] = set()
    public_base_url = os.getenv("PUBLIC_BASE_URL")
    if public_base_url:
        origins.add(public_base_url.rstrip("/"))
    if settings.API_ENV != "production":
        origins.update(
            {
                "http://localhost",
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            }
        )
    return sorted(origins)


app = FastAPI(
    title="API PAC Qualidade DELPI",
    description="API transacional de planos de ação central de qualidade (agente GPT).",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=build_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(pac_auth_middleware)
app.openapi = lambda: build_openapi_schema(app)
app.include_router(intelligence_router)
app.include_router(action_plans_router)


@app.get("/health", include_in_schema=False)
def health():
    plugins_ok = check_plugins_connection()
    delegation = get_pac_api_delpi_delegation_service()
    delegation_status = "enabled" if delegation.enabled() else "disabled"
    if settings.PAC_DELEGATE_TRANSACTIONAL_TO_API_DELPI and not delegation.enabled():
        delegation_status = "misconfigured"
    core_directory = CoreApiDirectoryGateway().configured()
    status = "ok" if plugins_ok or delegation.enabled() else "degraded"
    return {
        "status": status,
        "service": "api-pac-quality",
        "plugins_database": "ok" if plugins_ok else "unavailable",
        "api_delpi_delegation": delegation_status,
        "core_api_directory": "configured" if core_directory else "not_configured",
    }


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return not_found_response(str(exc.detail))
    return error_response(str(exc.detail), status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    return error_response(
        "Payload inválido.",
        status_code=422,
        code="VALIDATION_ERROR",
        meta={"details": jsonable_encoder(exc.errors())},
    )
