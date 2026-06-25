#!/usr/bin/env python3
"""Valida catálogo de evals PAC e pontua respostas estáticas (Onda 5.4/5.5).

CI (sem LLM):

  python scripts/run_pac_agent_eval.py --check-catalog

Homologação manual (após rodar cenários no GPT, salvar JSON):

  python scripts/run_pac_agent_eval.py --score-file eval_responses.json --min-pass-rate 0.9

Formato de `eval_responses.json`:

  [
    {"id": "EVAL01", "response": "texto completo da resposta do agente..."},
    ...
  ]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.domain.services.pac_agent_eval_policy_service import PacAgentEvalPolicyService
from tests.fixtures.pac_agent_eval_cases import PAC_AGENT_EVAL_CASES


def _load_responses(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, list):
        raise ValueError("eval_responses deve ser uma lista JSON")

    return payload


def _index_cases() -> dict[str, dict]:
    return {str(item["id"]): item for item in PAC_AGENT_EVAL_CASES}


def check_catalog() -> int:
    errors = PacAgentEvalPolicyService.validate_catalog(PAC_AGENT_EVAL_CASES)

    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
        return 1

    print(
        json.dumps(
            {
                "ok": True,
                "caseCount": len(PAC_AGENT_EVAL_CASES),
                "categories": sorted(
                    {str(item.get("category")) for item in PAC_AGENT_EVAL_CASES}
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def score_responses(path: Path, *, min_pass_rate: float) -> int:
    cases = _index_cases()
    rows = _load_responses(path)

    results: list[dict] = []
    passed = 0
    missing: list[str] = []

    for row in rows:
        case_id = str(row.get("id") or "").strip()
        response = str(row.get("response") or "")

        if not case_id:
            continue

        case = cases.get(case_id)

        if case is None:
            missing.append(case_id)
            continue

        evaluation = PacAgentEvalPolicyService.evaluate_response(case, response)
        results.append(
            {
                "id": case_id,
                "passed": evaluation.passed,
                "violations": evaluation.violations,
            }
        )

        if evaluation.passed:
            passed += 1

    evaluated = len(results)
    pass_rate = (passed / evaluated) if evaluated else 0.0
    ok = not missing and evaluated == len(cases) and pass_rate >= min_pass_rate

    report = {
        "ok": ok,
        "evaluated": evaluated,
        "expected": len(cases),
        "passed": passed,
        "passRate": round(pass_rate, 4),
        "minPassRate": min_pass_rate,
        "missingCaseIds": sorted(set(cases.keys()) - {r["id"] for r in results}),
        "unknownCaseIds": missing,
        "failures": [item for item in results if not item["passed"]],
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-catalog", action="store_true", help="Valida fixtures EVAL01–EVAL20.")
    parser.add_argument(
        "--score-file",
        type=Path,
        help="JSON com respostas do agente para pontuação estática.",
    )
    parser.add_argument(
        "--min-pass-rate",
        type=float,
        default=0.9,
        help="Taxa mínima de aprovação (default 0.9 = 90%%).",
    )
    args = parser.parse_args()

    if args.check_catalog:
        return check_catalog()

    if args.score_file:
        return score_responses(args.score_file, min_pass_rate=args.min_pass_rate)

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
