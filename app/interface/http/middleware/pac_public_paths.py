from __future__ import annotations

_PUBLIC_PATHS = frozenset(
    {
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
    }
)

_PUBLIC_SUFFIXES = (
    "/docs",
    "/docs/",
    "/redoc",
    "/redoc/",
    "/openapi.json",
    "/health",
)


def normalize_path(path: str) -> str:
    if not path:
        return "/"

    normalized = path.split("?", 1)[0]

    if normalized != "/" and normalized.endswith("/"):
        normalized = normalized.rstrip("/")

    return normalized


def is_public_path(path: str) -> bool:
    raw_path = path.split("?", 1)[0]
    normalized = normalize_path(path)

    return (
        raw_path.endswith(_PUBLIC_SUFFIXES)
        or normalized in _PUBLIC_PATHS
        or any(normalized.endswith(public_path) for public_path in _PUBLIC_PATHS)
    )
