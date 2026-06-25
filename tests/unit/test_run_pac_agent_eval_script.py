"""Gate do script run_pac_agent_eval.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_script():
    path = Path(__file__).resolve().parents[2] / "scripts" / "run_pac_agent_eval.py"
    spec = importlib.util.spec_from_file_location("run_pac_agent_eval", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_check_catalog_passes():
    script = _load_script()
    assert script.check_catalog() == 0


def test_score_sample_responses():
    script = _load_script()
    sample = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "pac_agent_eval_responses_sample.json"
    )

    exit_code = script.score_responses(sample, min_pass_rate=0.5)

    assert exit_code == 1  # amostra parcial — falta cobrir os 20 casos


def test_score_partial_sample_reports_missing():
    from app.domain.services.pac_agent_eval_policy_service import PacAgentEvalPolicyService

    script = _load_script()
    sample = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "pac_agent_eval_responses_sample.json"
    )
    cases = script._index_cases()
    rows = script._load_responses(sample)
    evaluated = [
        PacAgentEvalPolicyService.evaluate_response(cases[str(row["id"])], str(row["response"]))
        for row in rows
        if str(row.get("id")) in cases
    ]

    assert all(item.passed for item in evaluated)
