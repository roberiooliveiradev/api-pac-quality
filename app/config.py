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


settings = Settings()
