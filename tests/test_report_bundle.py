#!/usr/bin/env python
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_benchmark import (  # noqa: E402
    build_comparison_summary,
    classify_capability_result,
    classify_conformance_result,
    summarize_response_for_report,
    write_markdown_summary,
    write_comparison_bundle,
)
from render_html_report import render_html_report  # noqa: E402


class ReportBundleTests(unittest.TestCase):
    def test_classify_conformance_result_preserves_warning_and_unsupported(self) -> None:
        self.assertEqual(classify_conformance_result({"conformance_status": "PASS"}), "PASS")
        self.assertEqual(classify_conformance_result({"conformance_status": "UNSUPPORTED"}), "UNSUPPORTED")
        self.assertEqual(classify_conformance_result({"conformance_status": "WARNING"}), "WARNING")
        self.assertEqual(classify_conformance_result({"conformance_status": "weird"}), "FAIL")

    def test_classify_capability_result_matches_pass_and_fail_logic(self) -> None:
        passing = {
            "fail_requests": 0,
            "unsupported_requests": 0,
            "warning_requests": 0,
            "timeout_requests": 0,
            "timed_ok_requests": 5,
            "status_counts": {"200": 5},
        }
        failing = {
            "fail_requests": 5,
            "unsupported_requests": 0,
            "warning_requests": 0,
            "timeout_requests": 0,
            "timed_ok_requests": 0,
            "status_counts": {"200": 5},
        }
        unsupported = {
            "fail_requests": 0,
            "unsupported_requests": 5,
            "warning_requests": 0,
            "timeout_requests": 0,
            "timed_ok_requests": 0,
            "status_counts": {"422": 5},
        }
        self.assertEqual(classify_capability_result(passing), "PASS")
        self.assertEqual(classify_capability_result(failing), "FAIL")
        self.assertEqual(classify_capability_result(unsupported), "UNSUPPORTED")

    def test_write_comparison_bundle_creates_summary_and_svgs(self) -> None:
        report = {
            "run_id": "TEST_20_abc123",
            "suite_id": "TPCQF",
            "scale": 20,
            "concurrency": 4,
            "repetitions": 2,
            "duration_seconds": 12.5,
            "started_utc": "2026-01-01T00:00:00+00:00",
            "ended_utc": "2026-01-01T00:00:12+00:00",
            "engines": [
                {
                    "name": "engine-a",
                    "adapter": "generic-cqf",
                    "base_url": "http://a",
                    "cqf_base_path": "/fhir",
                    "results": [
                        {"scenario_id": "CONF001", "scenario_name": "metadata", "test_type": "conformance", "conformance_status": "PASS"},
                        {
                            "scenario_id": "CAP001-P",
                            "scenario_name": "count",
                            "test_type": "capability",
                            "fail_requests": 0,
                            "unsupported_requests": 0,
                            "warning_requests": 0,
                            "timeout_requests": 0,
                            "timed_ok_requests": 10,
                            "status_counts": {"200": 10},
                            "latency_ms": {"p95": 12.0, "avg_p95_over_repetitions": 13.0},
                        },
                    ],
                },
                {
                    "name": "engine-b",
                    "adapter": "generic-cqf",
                    "base_url": "http://b",
                    "cqf_base_path": "/fhir",
                    "results": [
                        {"scenario_id": "CONF001", "scenario_name": "metadata", "test_type": "conformance", "conformance_status": "FAIL"},
                        {
                            "scenario_id": "CAP001-P",
                            "scenario_name": "count",
                            "test_type": "capability",
                            "fail_requests": 3,
                            "unsupported_requests": 0,
                            "warning_requests": 0,
                            "timeout_requests": 0,
                            "timed_ok_requests": 0,
                            "status_counts": {"200": 3},
                            "latency_ms": None,
                        },
                    ],
                },
            ],
        }
        summary = build_comparison_summary(report)
        self.assertEqual(summary["conformance_counts_by_engine"]["engine-a"]["PASS"], 1)
        self.assertEqual(summary["capability_counts_by_engine"]["engine-a"]["PASS"], 1)
        self.assertEqual(summary["capability_counts_by_engine"]["engine-b"]["FAIL"], 1)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_base = Path(tmpdir) / report["run_id"]
            written = write_comparison_bundle(report, out_base)
            self.assertEqual(len(written), 6)
            for path in written:
                self.assertTrue(path.exists(), path)
            summary_json = json.loads(out_base.with_suffix(".summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary_json["run_id"], report["run_id"])
            summary_md = out_base.with_suffix(".summary.md").read_text(encoding="utf-8")
            self.assertIn("Engine Overview", summary_md)
            self.assertIn("What This Report Shows", summary_md)
            self.assertIn("CAP001-P", summary_md)
            self.assertIn("<svg", summary_md)
            self.assertIn("Conformance outcome counts by engine", summary_md)
            svg_text = out_base.with_suffix(".capability-p95.svg").read_text(encoding="utf-8")
            self.assertIn("<svg", svg_text)
            # Branded, self-contained HTML report is emitted alongside the bundle.
            html_path = out_base.with_suffix(".report.html")
            self.assertIn(html_path, written)
            html_text = html_path.read_text(encoding="utf-8")
            self.assertIn("<!doctype html>", html_text)
            self.assertIn("CQF Bench Report", html_text)
            self.assertIn("CAP001-P", html_text)
            self.assertIn("Correct &amp; fast?", html_text)
            self.assertIn("Reproducible run", html_text)
            # HTML must be self-contained (no external stylesheet/script refs).
            self.assertNotIn("<link", html_text)
            self.assertNotIn("<script", html_text)

    def test_summarize_response_for_report_prefers_operation_outcome_diagnostics(self) -> None:
        raw = json.dumps(
            {
                "resourceType": "OperationOutcome",
                "issue": [
                    {
                        "severity": "error",
                        "code": "invalid",
                        "diagnostics": "Missing library/url/canonical parameter",
                    }
                ],
            }
        )
        summary = summarize_response_for_report(raw)
        self.assertIn("OperationOutcome", summary)
        self.assertIn("Missing library/url/canonical parameter", summary)

    def test_write_markdown_summary_includes_failure_details(self) -> None:
        report = {
            "run_id": "TEST_FAIL_DETAILS",
            "suite_id": "TPCQF",
            "scale": 20,
            "concurrency": 4,
            "duration_seconds": 5.0,
            "engines": [
                {
                    "name": "engine-a",
                    "results": [
                        {
                            "scenario_id": "CONF013",
                            "scenario_name": "GET /Library/$data-requirements conformance",
                            "test_type": "conformance",
                            "conformance_status": "FAIL",
                            "conformance_note": "4xx warning: server/config requires attention",
                            "status_counts": {"400": 5},
                            "endpoint_used": {
                                "effective_method": "GET",
                                "effective_path": "/cqf/Library/$data-requirements",
                            },
                            "failure_examples": [
                                {
                                    "category": "warning",
                                    "http_status": 400,
                                    "reason": "HTTP 400 warning",
                                    "response_excerpt": "OperationOutcome: error / invalid / Missing library/url/canonical parameter",
                                }
                            ],
                        },
                        {
                            "scenario_id": "CAP005-I",
                            "scenario_name": "Tuple populated from another define (inline)",
                            "test_type": "capability",
                            "fail_requests": 100,
                            "unsupported_requests": 0,
                            "warning_requests": 0,
                            "timeout_requests": 0,
                            "timed_ok_requests": 0,
                            "incorrect_result_failures": 100,
                            "incorrect_result_notes": [
                                "expected Parameters.parameter[0].valueInteger == 8",
                            ],
                            "status_counts": {"200": 100},
                            "endpoint_used": {
                                "effective_method": "POST",
                                "effective_path": "/cqf/Library/BenchCAP005I/$evaluate",
                            },
                            "failure_examples": [
                                {
                                    "category": "incorrect_result",
                                    "http_status": 200,
                                    "reason": "expected Parameters.parameter[0].valueInteger == 8",
                                    "response_excerpt": "Parameters: evaluation error: error / exception / Cannot invoke ...",
                                }
                            ],
                        },
                    ],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            out_md = Path(tmpdir) / "report.md"
            write_markdown_summary(report, out_md)
            text = out_md.read_text(encoding="utf-8")
            self.assertIn("## Failure Details", text)
            self.assertIn("CONF013", text)
            self.assertIn("Missing library/url/canonical parameter", text)
            self.assertIn("CAP005-I", text)
            self.assertIn("expected Parameters.parameter[0].valueInteger == 8", text)

    def test_write_markdown_summary_preserves_unsupported_conformance_label(self) -> None:
        report = {
            "run_id": "TEST_UNSUPPORTED_LABEL",
            "suite_id": "TPCQF",
            "scale": 1,
            "concurrency": 1,
            "duration_seconds": 1.0,
            "engines": [
                {
                    "name": "engine-a",
                    "results": [
                        {
                            "scenario_id": "CONF040",
                            "scenario_name": "GET /PlanDefinition/$apply conformance",
                            "test_type": "conformance",
                            "conformance_status": "UNSUPPORTED",
                            "conformance_note": "HTTP 422 unsupported",
                            "status_counts": {"422": 5},
                        }
                    ],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            out_md = Path(tmpdir) / "report.md"
            write_markdown_summary(report, out_md)
            text = out_md.read_text(encoding="utf-8")
            self.assertIn("| CONF040 | GET /PlanDefinition/$apply conformance | UNSUPPORTED |", text)

    def test_render_html_report_is_self_contained_and_branded(self) -> None:
        report = {
            "run_id": "TEST_20_html01",
            "suite_id": "TPCQF",
            "suite_hash": "deadbeefcafef00d",
            "git_commit": "abc1234",
            "scale": 20,
            "concurrency": 4,
            "repetitions": 2,
            "score_mode": "compat",
            "duration_seconds": 12.5,
            "started_utc": "2026-01-01T00:00:00+00:00",
            "ended_utc": "2026-01-01T00:00:12+00:00",
            "engines": [
                {
                    "name": "engine-a",
                    "adapter": "generic-cqf",
                    "base_url": "http://a",
                    "results": [
                        {"scenario_id": "CONF001", "scenario_name": "metadata", "test_type": "conformance", "conformance_status": "PASS"},
                        {
                            "scenario_id": "CAP001-P",
                            "scenario_name": "count",
                            "test_type": "capability",
                            "fail_requests": 0,
                            "unsupported_requests": 0,
                            "warning_requests": 0,
                            "timeout_requests": 0,
                            "timed_ok_requests": 10,
                            "status_counts": {"200": 10},
                            "latency_ms": {"min": 5.0, "p50": 8.0, "p95": 12.0, "p99": 14.0, "max": 18.0, "avg_p95_over_repetitions": 13.0},
                        },
                    ],
                },
            ],
        }
        out = render_html_report(report)
        # Self-contained: a complete document with no external CSS/JS/image refs.
        self.assertTrue(out.startswith("<!doctype html>"))
        self.assertNotIn("<link", out)
        self.assertNotIn("<script", out)
        # Branding + key sections present.
        self.assertIn("CQF Bench Report", out)
        self.assertIn("Carrera Group", out)
        self.assertIn("Scorecards", out)
        self.assertIn("CAP001-P", out)
        # Headline latency uses the canonical avg-p95-over-reps value (13.0ms), not raw p95.
        self.assertIn("13.0ms", out)
        # Provenance surfaced from the report.
        self.assertIn("deadbeefcafe", out)

    def test_render_html_report_handles_no_pass_latency(self) -> None:
        report = {
            "run_id": "TEST_20_html02",
            "suite_id": "TPCQF",
            "scale": 20,
            "engines": [
                {
                    "name": "engine-z",
                    "adapter": "generic-cqf",
                    "base_url": "http://z",
                    "results": [
                        {
                            "scenario_id": "CAP001-P",
                            "scenario_name": "count",
                            "test_type": "capability",
                            "fail_requests": 3,
                            "timed_ok_requests": 0,
                            "status_counts": {"500": 3},
                            "latency_ms": None,
                        },
                    ],
                },
            ],
        }
        # Must not raise even when no scenario passed / no latency to plot.
        out = render_html_report(report)
        self.assertIn("No PASS latency", out)
        self.assertIn("engine-z", out)


if __name__ == "__main__":
    unittest.main()
