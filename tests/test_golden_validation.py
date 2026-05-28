#!/usr/bin/env python
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_benchmark import (  # noqa: E402
    build_validation_context,
    compute_mix_counts,
    load_config,
    null_id_count_from_plan,
    run_response_validators,
    _eval_validation_expression,
)


class GoldenValidationTests(unittest.TestCase):
    def test_compute_mix_counts_default_plan(self) -> None:
        plan = load_config(ROOT / "bench/scenarios/tpcqf/CAP001-P/mutator.yaml")
        counts = compute_mix_counts(plan, 0.2)
        self.assertEqual(counts["ConditionMatch"], 8)
        self.assertEqual(counts["ConditionNoMatch"], 32)

    def test_eval_expression_round_and_subtract(self) -> None:
        ctx = {
            "total_count": 40,
            "selectivity": 0.2,
            "null_id_count": 2,
        }
        self.assertEqual(_eval_validation_expression("round(total_count * selectivity)", ctx), 8.0)
        self.assertEqual(_eval_validation_expression("total_count - null_id_count", ctx), 38.0)

    def test_build_validation_context_cap011(self) -> None:
        scenario = {
            "__base_dir": str(ROOT / "bench/scenarios/tpcqf/CAP011-P"),
            "id": "CAP011-P",
            "_data_config": load_config(ROOT / "bench/scenarios/tpcqf/CAP011-P/data.yaml"),
        }
        ctx = build_validation_context(scenario, ["p1"], 0.2)
        self.assertEqual(ctx["total_count"], 40)
        self.assertEqual(ctx["null_id_count"], 2)
        self.assertEqual(ctx["match_count"], 8)

    def test_cap006_mutator_has_no_nomatch_linked_obs(self) -> None:
        plan = load_config(ROOT / "bench/scenarios/tpcqf/CAP006-P/mutator.yaml")
        linked = plan.get("linked_templates", {})
        self.assertIn("ConditionMatch", linked)
        self.assertNotIn("ConditionNoMatch", linked)

    def test_tokenized_numeric_validator_pass_and_fail(self) -> None:
        raw = json.dumps(
            {
                "resourceType": "Parameters",
                "parameter": [{"name": "CountAllCondition", "valueInteger": 40}],
            }
        )
        cfg = {
            "when_status_in": [200],
            "validators": [
                {"type": "not_operation_outcome_error"},
                {
                    "type": "tokenized_numeric_equals",
                    "path": "$.parameter[*]",
                    "expression": "total_count",
                    "expected_type": "valueInteger",
                },
            ],
        }
        ok, _, failures = run_response_validators(raw, cfg, 200, {"total_count": 40, "selectivity": 0.2})
        self.assertTrue(ok, failures)

        bad = json.dumps(
            {
                "resourceType": "Parameters",
                "parameter": [{"name": "CountAllCondition", "valueInteger": 7}],
            }
        )
        ok2, _, failures2 = run_response_validators(bad, cfg, 200, {"total_count": 40, "selectivity": 0.2})
        self.assertFalse(ok2)
        self.assertTrue(failures2)

    def test_boolean_exists_validator(self) -> None:
        raw = json.dumps(
            {
                "resourceType": "Parameters",
                "parameter": [{"name": "ExistsManyResults", "valueBoolean": True}],
            }
        )
        cfg = {
            "when_status_in": [200],
            "validators": [
                {"type": "value_type_and_equals", "path": "$.parameter[*]", "expected_type": "valueBoolean", "expected_value": True, "mode": "any"},
            ],
        }
        ok, _, _ = run_response_validators(raw, cfg, 200, {})
        self.assertTrue(ok)

    def test_null_id_count_from_plan(self) -> None:
        plan = load_config(ROOT / "bench/scenarios/tpcqf/CAP011-P/mutator.yaml")
        self.assertEqual(null_id_count_from_plan(plan), 2)


if __name__ == "__main__":
    unittest.main()
