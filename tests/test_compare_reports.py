#!/usr/bin/env python
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from compare_reports import _merge_reports  # noqa: E402


class CompareReportsTests(unittest.TestCase):
    def test_merge_reports_combines_engines(self) -> None:
        report_a = {
            "run_id": "RUN_A",
            "suite_id": "TPCQF",
            "scale": 20,
            "engines": [{"name": "engine-a", "results": []}],
        }
        report_b = {
            "run_id": "RUN_B",
            "suite_id": "TPCQF",
            "scale": 20,
            "engines": [{"name": "engine-b", "results": []}],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path_a = Path(tmpdir) / "a.json"
            path_b = Path(tmpdir) / "b.json"
            path_a.write_text(json.dumps(report_a), encoding="utf-8")
            path_b.write_text(json.dumps(report_b), encoding="utf-8")
            merged = _merge_reports([path_a, path_b])
        self.assertEqual(merged["run_id"], "RUN_A")
        self.assertEqual(len(merged["engines"]), 2)
        self.assertEqual(merged["engines"][1]["name"], "engine-b")
        self.assertEqual(merged["source_reports"], [str(path_a), str(path_b)])


if __name__ == "__main__":
    unittest.main()
