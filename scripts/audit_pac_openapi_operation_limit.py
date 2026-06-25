#!/usr/bin/env python3
"""Gate — OpenAPI api-pac-quality expõe só o fluxo analista (≤30 operações ChatGPT)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.interface.http.route_contract_registry import (  # noqa: E402
    ANALYST_PAC_OPERATION_IDS,
    CHATGPT_MAX_OPENAPI_OPERATIONS,
)
from app.interface.http.openapi_schema import build_openapi_schema  # noqa: E402
from app.main import app  # noqa: E402


def _operation_ids(schema: dict) -> set[str]:
    rows: set[str] = set()
    paths = schema.get("paths")

    if not isinstance(paths, dict):
        return rows

    for path_item in paths.values():
        if not isinstance(path_item, dict):
            continue

        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue

            operation_id = str(operation.get("operationId") or "").strip()

            if operation_id:
                rows.add(operation_id)

    return rows


def validate(schema: dict) -> dict:
    published = _operation_ids(schema)
    extra = sorted(published - ANALYST_PAC_OPERATION_IDS)
    missing = sorted(ANALYST_PAC_OPERATION_IDS - published)
    ok = (
        not extra
        and not missing
        and len(published) == len(ANALYST_PAC_OPERATION_IDS)
        and len(published) <= CHATGPT_MAX_OPENAPI_OPERATIONS
        and "/health" not in (schema.get("paths") or {})
    )

    return {
        "ok": ok,
        "operationCount": len(published),
        "maxOperations": CHATGPT_MAX_OPENAPI_OPERATIONS,
        "expectedCount": len(ANALYST_PAC_OPERATION_IDS),
        "extraOperationIds": extra,
        "missingOperationIds": missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--openapi-url",
        default=os.environ.get("PAC_OPENAPI_URL", ""),
        help="URL remota (opcional). Sem URL, valida schema local.",
    )
    args = parser.parse_args()

    if args.openapi_url:
        with urllib.request.urlopen(args.openapi_url, timeout=60) as response:
            schema = json.loads(response.read().decode("utf-8"))
    else:
        schema = build_openapi_schema(app)

    report = validate(schema)

    if args.check:
        if report["ok"]:
            print(
                "OK pac openapi analyst",
                json.dumps(
                    {
                        "operationCount": report["operationCount"],
                        "maxOperations": report["maxOperations"],
                    },
                    ensure_ascii=False,
                ),
            )
            return 0

        print(json.dumps(report, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
