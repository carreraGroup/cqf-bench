#!/usr/bin/env python
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_benchmark import (  # noqa: E402
    ADAPTERS,
    apply_generated_corpus_main_overrides,
    canonical_json_text,
    compile_inline_payload_from_assembly,
    generate_scenario_payload_files,
    load_config,
    load_phase_assembly_spec,
    load_suite_with_scenarios,
    order_scenarios_for_execution,
    read_dataset_manifest,
    run_scenario,
    sha256_hex,
)


class UnifiedCorpusTests(unittest.TestCase):
    maxDiff = None

    def _generate_tree(self, scale: int = 2, selectivity: float = 0.2) -> Path:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        out_root = Path(tmpdir.name) / "generated"
        rc = generate_scenario_payload_files(out_root, scale, selectivity)
        self.assertEqual(rc, 0)
        return out_root

    def _inline_scenarios(self) -> list[dict[str, object]]:
        _, scenarios, _ = load_suite_with_scenarios(ROOT / "bench/scenarios/tpcqf/suite.yaml")
        return [scenario for scenario in scenarios if str(scenario.get("id", "")).endswith("-I")]

    def test_generated_tree_has_expected_manifest_and_paths(self) -> None:
        out_root = self._generate_tree()
        manifest = read_dataset_manifest(out_root)
        self.assertIsNotNone(manifest)
        assert manifest is not None
        self.assertEqual(manifest["layout"], "unified-corpus-v3")
        self.assertEqual(manifest["scale"], 2)
        self.assertEqual(manifest["selectivity"], 0.2)
        self.assertEqual(manifest["corpus_setup_path"], "corpus/setup/<patient_id>.json")
        self.assertEqual(manifest["corpus_preload_path"], "corpus/preload/<scenario_id>/setup/<patient_id>.json")
        self.assertEqual(manifest["corpus_inline_path"], "corpus/inline/<scenario_id>/<patient_id>.json")
        self.assertEqual(manifest["coverage_manifest_path"], "corpus_coverage.json")
        self.assertEqual(manifest["starter_bundle_path"], "corpus/starter/p1.json")
        self.assertTrue((out_root / "corpus" / "starter" / "p1.json").is_file())
        self.assertTrue((out_root / "corpus_coverage.json").is_file())
        self.assertTrue((out_root / "corpus" / "preload" / "CAP001-P" / "setup" / "p1.json").is_file())

    def test_setup_bundles_are_transaction_bundles_with_deduped_ids(self) -> None:
        out_root = self._generate_tree()
        for patient_id in ("p1", "p2"):
            payload = json.loads((out_root / "corpus" / "setup" / f"{patient_id}.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["resourceType"], "Bundle")
            self.assertEqual(payload["type"], "transaction")
            seen: set[tuple[str, str]] = set()
            resource_types: set[str] = set()
            for entry in payload["entry"]:
                self.assertIn("resource", entry)
                resource = entry["resource"]
                self.assertIsInstance(resource, dict)
                resource_types.add(str(resource.get("resourceType", "")))
                rid = resource.get("id")
                if resource.get("resourceType") and rid:
                    key = (str(resource["resourceType"]), str(rid))
                    self.assertNotIn(key, seen)
                    seen.add(key)
            self.assertIn("Patient", resource_types)
            self.assertIn("Condition", resource_types)

    def test_inline_payloads_exist_and_match_output_mode(self) -> None:
        out_root = self._generate_tree()
        for scenario in self._inline_scenarios():
            sid = str(scenario["id"])
            assembly = load_phase_assembly_spec(scenario, scenario.get("_data_config"), "main")
            self.assertIsNotNone(assembly)
            assert assembly is not None
            output_mode = str(assembly.get("output_mode", "bundle"))
            for patient_id in ("p1", "p2"):
                path = out_root / "corpus" / "inline" / sid / f"{patient_id}.json"
                self.assertTrue(path.is_file(), path)
                payload = json.loads(path.read_text(encoding="utf-8"))
                if output_mode == "parameters_data":
                    self.assertEqual(payload["resourceType"], "Parameters")
                    params = payload.get("parameter", [])
                    self.assertTrue(any(p.get("name") == "data" for p in params if isinstance(p, dict)))
                else:
                    self.assertEqual(payload["resourceType"], "Bundle")

    def test_coverage_manifest_emitted_and_valid(self) -> None:
        out_root = self._generate_tree()
        coverage = json.loads((out_root / "corpus_coverage.json").read_text(encoding="utf-8"))
        rows = coverage["rows"]
        self.assertEqual(coverage["version"], 1)
        self.assertEqual(coverage["shared_resource_conflicts"], {})
        self.assertEqual(len(rows), len(self._inline_scenarios()) * 2)
        first = rows[0]
        self.assertIn("scenario_id", first)
        self.assertIn("required_resource_keys", first)
        self.assertIn("required_type_counts", first)
        self.assertGreater(len(first["required_resource_keys"]), 0)

    def test_inline_round_trip_matches_snapshot_hash(self) -> None:
        out_root = self._generate_tree()
        suite, scenarios, _ = load_suite_with_scenarios(ROOT / "bench/scenarios/tpcqf/suite.yaml")
        scenario = next(s for s in scenarios if s["id"] == "CAP001-I")
        resident_bundle = json.loads((out_root / "corpus" / "setup" / "p1.json").read_text(encoding="utf-8"))
        compiled = compile_inline_payload_from_assembly(scenario, "p1", 0.2, resident_bundle)
        on_disk = json.loads((out_root / "corpus" / "inline" / "CAP001-I" / "p1.json").read_text(encoding="utf-8"))
        self.assertEqual(canonical_json_text(compiled), canonical_json_text(on_disk))

        fixture = json.loads((ROOT / "tests" / "fixtures" / "unified_corpus_hashes.json").read_text(encoding="utf-8"))
        expected_hash = fixture["scale2_sel0.2"]["CAP001-I/p1"]
        self.assertEqual(sha256_hex(canonical_json_text(on_disk)), expected_hash)
        self.assertEqual(suite["suite_id"], "TPCQF")

    def test_generation_is_deterministic_for_fixed_inputs(self) -> None:
        root_a = self._generate_tree()
        root_b = self._generate_tree()
        compare_paths = [
            "dataset.json",
            "corpus_coverage.json",
            "corpus/starter/p1.json",
            "corpus/setup/p1.json",
            "corpus/setup/p2.json",
            "corpus/inline/CAP001-I/p1.json",
            "corpus/inline/CAP011-I/p2.json",
        ]
        for rel in compare_paths:
            text_a = json.loads((root_a / rel).read_text(encoding="utf-8"))
            text_b = json.loads((root_b / rel).read_text(encoding="utf-8"))
            self.assertEqual(canonical_json_text(text_a), canonical_json_text(text_b), rel)

    def test_fake_harness_behavior_for_conf_preload_and_inline(self) -> None:
        out_root = self._generate_tree(scale=1)
        suite, scenarios, _ = load_suite_with_scenarios(ROOT / "bench/scenarios/tpcqf/suite.yaml")
        ordered = order_scenarios_for_execution(scenarios)
        conf = next(s for s in ordered if s["id"] == "CONF010")
        preload = next(s for s in ordered if s["id"] == "CAP001-P")
        inline = next(s for s in apply_generated_corpus_main_overrides(ordered, out_root) if s["id"] == "CAP001-I")

        engine = {"base_url": "http://localhost:8081", "cqf_base_path": "/fhir", "data_base_path": "/fhir", "fhir_base_path": "/fhir", "headers": {}}
        adapter = ADAPTERS["generic-cqf"]

        conf_requests: list[tuple[str, str, object | None]] = []
        cap_requests: list[tuple[str, str, object | None]] = []

        def fake_conf_request(method, url, headers, payload, timeout, content_type):  # type: ignore[no-untyped-def]
            conf_requests.append((method, url, payload))
            return 200, 1.0, "{}"

        def fake_cap_request(method, url, headers, payload, timeout, content_type):  # type: ignore[no-untyped-def]
            cap_requests.append((method, url, payload))
            raw = json.dumps({"resourceType": "Parameters", "parameter": [{"name": "CountAllCondition", "valueInteger": 40}]})
            if method == "POST" and "/Bundle" in url:
                return 201, 1.0, ""
            return 200, 1.0, raw

        with patch("run_benchmark.request_once", side_effect=fake_conf_request):
            conf_result = run_scenario(
                engine,
                conf,
                ["p1"],
                concurrency=1,
                timeout=30,
                adapter=adapter,
                repetitions=1,
                selectivity=0.2,
                suite_defaults=suite,
            )
        self.assertEqual(conf_result["conformance_status"], "PASS")
        self.assertEqual(conf_requests[0][0], "GET")

        preload_execute = copy.deepcopy(preload)
        preload_execute.pop("setup", None)
        with patch("run_benchmark.request_once", side_effect=fake_cap_request), patch(
            "run_benchmark._cleanup_inline_main_payloads", return_value=None
        ):
            preload_result = run_scenario(
                engine,
                preload_execute,
                ["p1"],
                concurrency=1,
                timeout=30,
                adapter=adapter,
                repetitions=1,
                selectivity=0.2,
                suite_defaults=suite,
            )
        self.assertEqual(preload_result["validate_eligible_requests"], 1)
        self.assertEqual(preload_result["timed_ok_requests"], 1)
        self.assertEqual(cap_requests[0][0], "GET")
        self.assertIn("/fhir/Library/$evaluate?", cap_requests[0][1])

        cap_requests.clear()
        with patch("run_benchmark.request_once", side_effect=fake_cap_request), patch(
            "run_benchmark.setup_for_scenario", return_value=None
        ), patch("run_benchmark._cleanup_inline_main_payloads", return_value=None):
            inline_result = run_scenario(
                engine,
                inline,
                ["p1"],
                concurrency=1,
                timeout=30,
                adapter=adapter,
                repetitions=1,
                selectivity=0.2,
                suite_defaults=suite,
            )
        self.assertEqual(inline_result["validate_eligible_requests"], 1)
        self.assertEqual(inline_result["timed_ok_requests"], 1)
        self.assertEqual(cap_requests[0][0], "POST")
        self.assertIn("/fhir/Library/$evaluate?", cap_requests[0][1])
        self.assertIsInstance(cap_requests[0][2], dict)


if __name__ == "__main__":
    unittest.main()
