#!/usr/bin/env python
from __future__ import annotations

import json
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_benchmark import (  # noqa: E402
    _payload_from_data_config,
    _cleanup_inline_main_payloads,
    _cleanup_setup_target,
    _extract_patient_cleanup_targets,
    apply_generated_data_root_overrides,
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

    def test_generated_data_override_resolves_from_repo_root(self) -> None:
        scenario = {
            "id": "CAP001-P",
            "__base_dir": str(ROOT / "bench/scenarios/tpcqf/CAP001-P"),
            "_data_config": load_config(ROOT / "bench/scenarios/tpcqf/CAP001-P/data.yaml"),
        }
        updated = apply_generated_data_root_overrides(
            [scenario],
            ROOT / "data/generated/final_tpcqf_s100_sel20_20260604",
            use_setup_phase=True,
            use_main_phase=False,
        )[0]
        payload = _payload_from_data_config(updated, updated["_data_config"], "p1", 0.2, "setup")
        self.assertIsInstance(payload, dict)
        self.assertEqual("Bundle", payload.get("resourceType"))

    def test_generated_data_override_preserves_mutator_plan_for_validation_context(self) -> None:
        scenario = {
            "id": "CAP011-I",
            "__base_dir": str(ROOT / "bench/scenarios/tpcqf/CAP011-I"),
            "_data_config": load_config(ROOT / "bench/scenarios/tpcqf/CAP011-I/data.yaml"),
        }
        updated = apply_generated_data_root_overrides(
            [scenario],
            ROOT / "data/generated/repeatability_s20_sel20",
            use_setup_phase=False,
            use_main_phase=True,
        )[0]
        ctx = build_validation_context(updated, ["p1"], 0.2)
        self.assertEqual(ctx["total_count"], 40)
        self.assertEqual(ctx["null_id_count"], 2)
        self.assertEqual(ctx["match_count"], 8)

    def test_min_items_validator_supports_alt_paths(self) -> None:
        raw = json.dumps(
            {
                "resourceType": "Parameters",
                "parameter": [{"name": "ReturnConditionIds", "valueString": f"cond-{idx}"} for idx in range(40)],
            }
        )
        cfg = {
            "when_status_in": [200],
            "validators": [
                {"type": "not_operation_outcome_error"},
                {
                    "type": "min_items",
                    "path": "$.parameter[?(@.name=='ReturnConditionIds')].part[*]",
                    "alt_paths": ["$.parameter[?(@.name=='ReturnConditionIds')]"],
                    "min": 40,
                },
            ],
        }
        ok, _, failures = run_response_validators(raw, cfg, 200, {})
        self.assertTrue(ok, failures)

    def test_extract_patient_cleanup_targets(self) -> None:
        payload = {
            "resourceType": "Bundle",
            "entry": [
                {"resource": {"resourceType": "Patient", "id": "p1"}},
                {"resource": {"resourceType": "Condition", "id": "cond-1", "subject": {"reference": "Patient/p1"}}},
                {"resource": {"resourceType": "Observation", "id": "obs-1", "subject": {"reference": "Patient/p1"}}},
                {"resource": {"resourceType": "Encounter", "id": "enc-1", "patient": {"reference": "Patient/p1"}}},
            ],
        }
        self.assertEqual(
            _extract_patient_cleanup_targets(payload),
            [("Condition", "Patient/p1"), ("Observation", "Patient/p1"), ("Encounter", "Patient/p1")],
        )

    def test_extract_patient_cleanup_targets_from_parameters_data_bundle(self) -> None:
        payload = {
            "resourceType": "Parameters",
            "parameter": [
                {
                    "name": "data",
                    "resource": {
                        "resourceType": "Bundle",
                        "entry": [
                            {"resource": {"resourceType": "Patient", "id": "p1"}},
                            {"resource": {"resourceType": "Condition", "id": "cond-1", "subject": {"reference": "Patient/p1"}}},
                        ],
                    },
                }
            ],
        }
        self.assertEqual(_extract_patient_cleanup_targets(payload), [("Condition", "Patient/p1")])

    def test_cleanup_setup_target_deletes_patient_scoped_search_results(self) -> None:
        payload = {
            "resourceType": "Bundle",
            "entry": [
                {"resource": {"resourceType": "Patient", "id": "p1"}},
                {"resource": {"resourceType": "Condition", "id": "cond-new", "subject": {"reference": "Patient/p1"}}},
                {"resource": {"resourceType": "Observation", "id": "obs-new", "subject": {"reference": "Patient/p1"}}},
            ],
        }
        engine = {"base_url": "http://localhost:8081", "fhir_base_path": "/fhir", "data_base_path": "/fhir", "headers": {}}
        requests: list[tuple[str, str]] = []

        def fake_request_once(method, url, headers, payload, timeout, content_type):  # type: ignore[no-untyped-def]
            requests.append((method, url))
            if method == "GET" and "Condition?" in url:
                return 200, 1.0, json.dumps(
                    {"resourceType": "Bundle", "entry": [{"resource": {"resourceType": "Condition", "id": "cond-old"}}]}
                )
            if method == "GET" and "Observation?" in url:
                return 200, 1.0, json.dumps(
                    {"resourceType": "Bundle", "entry": [{"resource": {"resourceType": "Observation", "id": "obs-old"}}]}
                )
            return 200, 1.0, ""

        with patch("run_benchmark.request_once", side_effect=fake_request_once):
            _cleanup_setup_target(
                engine,
                {"path_role": "data"},
                "p1",
                30,
                payload,
            )

        self.assertIn(("GET", "http://localhost:8081/fhir/Condition?subject=Patient%2Fp1&_count=200"), requests)
        self.assertIn(("GET", "http://localhost:8081/fhir/Observation?subject=Patient%2Fp1&_count=200"), requests)
        self.assertIn(("DELETE", "http://localhost:8081/fhir/Condition/cond-old"), requests)
        self.assertIn(("DELETE", "http://localhost:8081/fhir/Observation/obs-old"), requests)
        self.assertIn(("DELETE", "http://localhost:8081/fhir/Condition/cond-new"), requests)
        self.assertIn(("DELETE", "http://localhost:8081/fhir/Observation/obs-new"), requests)
        self.assertIn(("DELETE", "http://localhost:8081/fhir/Patient/p1"), requests)

    def test_cleanup_inline_main_payloads_uses_parameters_embedded_bundle(self) -> None:
        scenario = {
            "id": "CAP001-I",
            "method": "POST",
            "path": "/Library/$evaluate",
            "setup": None,
            "_data_config": {},
        }
        engine = {"base_url": "http://localhost:8081", "fhir_base_path": "/fhir", "data_base_path": "/fhir", "headers": {}}

        class DummyAdapter:
            def payload_from_query(self, scenario, patient_id, phase="main"):  # type: ignore[no-untyped-def]
                return None

        requests: list[tuple[str, str]] = []
        payload = {
            "resourceType": "Parameters",
            "parameter": [
                {
                    "name": "data",
                    "resource": {
                        "resourceType": "Bundle",
                        "entry": [
                            {"resource": {"resourceType": "Patient", "id": "p1"}},
                            {"resource": {"resourceType": "Condition", "id": "cond-inline", "subject": {"reference": "Patient/p1"}}},
                        ],
                    },
                }
            ],
        }

        def fake_request_once(method, url, headers, payload_arg, timeout, content_type):  # type: ignore[no-untyped-def]
            requests.append((method, url))
            if method == "GET" and "Condition?" in url:
                return 200, 1.0, json.dumps(
                    {"resourceType": "Bundle", "entry": [{"resource": {"resourceType": "Condition", "id": "cond-old"}}]}
                )
            return 200, 1.0, ""

        with patch("run_benchmark.prepare_payload", return_value=payload), patch("run_benchmark.request_once", side_effect=fake_request_once):
            _cleanup_inline_main_payloads(
                engine,
                scenario,
                ["p1"],
                30,
                DummyAdapter(),
                0.2,
            )

        self.assertIn(("GET", "http://localhost:8081/fhir/Condition?subject=Patient%2Fp1&_count=200"), requests)
        self.assertIn(("DELETE", "http://localhost:8081/fhir/Condition/cond-old"), requests)
        self.assertIn(("DELETE", "http://localhost:8081/fhir/Condition/cond-inline"), requests)
        self.assertIn(("DELETE", "http://localhost:8081/fhir/Patient/p1"), requests)


if __name__ == "__main__":
    unittest.main()
