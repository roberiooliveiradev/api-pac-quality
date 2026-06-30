#!/usr/bin/env python3
"""Gate Onda 1 PAC — paridade OpenAPI api-pac-quality (rotas 8D/evidências)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ONDA1_PAC_OPERATION_IDS = (
    "pac_create_action_plan",
    "pac_update_action_plan",
    "pac_upsert_rnc_8d",
    "pac_export_rnc_8d",
    "pac_list_plan_evidences",
    "pac_attach_plan_evidence",
    "pac_get_plan_evidence_content",
    "pac_delete_plan_evidence",
    "pac_download_plan_evidence",
    "pac_upsert_ishikawa",
    "pac_upsert_five_whys",
    "pac_create_plan_actions",
    "pac_update_plan_action",
    "pac_delete_plan_action",
)

ONDA1_PAC_PATHS = (
    "/quality/action-plans",
    "/quality/action-plans/{plan_id}",
    "/quality/action-plans/{plan_id}/rnc-8d",
    "/quality/action-plans/{plan_id}/export/rnc-8d",
    "/quality/action-plans/{plan_id}/evidences",
    "/quality/action-plans/{plan_id}/evidences/{evidence_id}",
    "/quality/action-plans/{plan_id}/evidences/{evidence_id}/file",
    "/quality/action-plans/{plan_id}/evidences/{evidence_id}/content",
)


def _load_schema(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("OpenAPI inválido")
    return payload


def validate(schema: dict) -> dict:
    paths = schema.get("paths") if isinstance(schema.get("paths"), dict) else {}
    missing_paths = [path for path in ONDA1_PAC_PATHS if path not in paths]

    operations: dict[str, dict] = {}
    for path_item in paths.values():
        if not isinstance(path_item, dict):
            continue
        for operation in path_item.values():
            if isinstance(operation, dict):
                operation_id = str(operation.get("operationId") or "").strip()
                if operation_id:
                    operations[operation_id] = operation

    missing_operation_ids = [
        operation_id for operation_id in ONDA1_PAC_OPERATION_IDS if operation_id not in operations
    ]

    ok = not missing_paths and not missing_operation_ids
    return {
        "ok": ok,
        "missingPaths": missing_paths,
        "missingOperationIds": missing_operation_ids,
        "operationCount": len(operations),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--openapi-url",
        default=os.environ.get("PAC_OPENAPI_URL", "http://127.0.0.1:8010/openapi.json"),
    )
    args = parser.parse_args()

    try:
        report = validate(_load_schema(args.openapi_url))
    except (OSError, urllib.error.URLError, json.JSONDecodeError, ValueError) as exc:
        report = {"ok": False, "error": str(exc)}

    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.check and not report.get("ok"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
