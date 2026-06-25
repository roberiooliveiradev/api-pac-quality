import os
from dotenv import load_dotenv

load_dotenv()


def _get_env(*names: str, default=None):
    for name in names:
        value = os.getenv(name)
        if value is not None and value != "":
            return value
    return default


class Settings:
    PORT: str = _get_env("API_PAC_QUALITY_PORT", "PORT", default="8010")
    API_ENV: str = _get_env("API_PAC_QUALITY_ENV", default="development")
    LOG_LEVEL: str = _get_env("LOG_LEVEL", default="INFO")
    ROOT_PATH: str = _get_env("API_PAC_ROOT_PATH", default="")
    PUBLIC_BASE_URL: str | None = _get_env("PUBLIC_BASE_URL")
    PAC_QUALITY_API_KEY: str | None = _get_env("PAC_QUALITY_API_KEY")

    KEYCLOAK_JWKS_URL: str | None = _get_env("KEYCLOAK_JWKS_URL")
    KEYCLOAK_ISSUER: str | None = _get_env("KEYCLOAK_ISSUER")
    KEYCLOAK_AUDIENCE: str | None = _get_env("KEYCLOAK_AUDIENCE")
    JWT_ALGORITHMS: str = _get_env("JWT_ALGORITHMS", default="RS256")

    PLUGINS_DB_HOST: str | None = _get_env("PLUGINS_DB_HOST")
    PLUGINS_DB_PORT: str = _get_env("PLUGINS_DB_PORT", default="5432")
    PLUGINS_DB_NAME: str | None = _get_env("PLUGINS_DB_NAME")
    PLUGINS_DB_USER: str | None = _get_env("PLUGINS_DB_USER")
    PLUGINS_DB_PASSWORD: str | None = _get_env("PLUGINS_DB_PASSWORD")
    PLUGINS_DB_CONNECT_TIMEOUT: str = _get_env("PLUGINS_DB_CONNECT_TIMEOUT", default="5")
    PLUGINS_DB_SSLMODE: str = _get_env("PLUGINS_DB_SSLMODE", default="prefer")

    PAC_EVIDENCE_UPLOAD_DIR: str = _get_env(
        "PAC_EVIDENCE_UPLOAD_DIR",
        default="/app/data/pac-quality-evidences",
    )

    CORE_API_BASE_URL: str | None = _get_env("CORE_API_BASE_URL", default="http://core-api:8000")
    CORE_API_INTEGRATIONS_SERVICE_TOKEN: str | None = _get_env(
        "CORE_API_INTEGRATIONS_SERVICE_TOKEN"
    )
    PAC_QUALITY_NOTIFICATIONS_ENABLED: bool = (
        _get_env("PAC_QUALITY_NOTIFICATIONS_ENABLED", default="true").lower() == "true"
    )
    PAC_QUALITY_ACTION_DUE_DAYS_AHEAD: int = int(
        _get_env("PAC_QUALITY_ACTION_DUE_DAYS_AHEAD", default="2") or "2"
    )
    PAC_QUALITY_STALL_DAYS: int = int(
        _get_env("PAC_QUALITY_STALL_DAYS", default="5") or "5"
    )
    PAC_QUALITY_COORDINATOR_USER_IDS: str | None = _get_env("PAC_QUALITY_COORDINATOR_USER_IDS")

    OLLAMA_BASE_URL: str | None = _get_env("OLLAMA_BASE_URL", default="http://ollama:11434")
    EMBEDDING_MODEL: str = _get_env("EMBEDDING_MODEL", default="bge-m3")
    EMBEDDING_DIMENSIONS: int = int(_get_env("EMBEDDING_DIMENSIONS", default="1024") or "1024")
    EMBEDDING_TIMEOUT_SECONDS: float = float(
        _get_env("EMBEDDING_TIMEOUT_SECONDS", default="30") or "30"
    )
    PAC_SIMILARITY_EMBEDDINGS_ENABLED: bool = (
        _get_env("PAC_SIMILARITY_EMBEDDINGS_ENABLED", default="false").lower() == "true"
    )


settings = Settings()
