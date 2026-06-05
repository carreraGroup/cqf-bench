#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_benchmark import write_comparison_bundle, write_markdown_summary  # noqa: E402


def _merge_reports(report_paths: list[Path]) -> dict[str, Any]:
    docs = [json.loads(path.read_text(encoding="utf-8")) for path in report_paths]
    if not docs:
        raise ValueError("No reports provided")

    base = dict(docs[0])
    merged_engines: list[dict[str, Any]] = []
    for doc in docs:
        for engine in doc.get("engines", []):
            merged_engines.append(engine)

    base["engines"] = merged_engines
    base["source_reports"] = [str(path) for path in report_paths]
    base["merged_from_runs"] = [str(doc.get("run_id", "")) for doc in docs]
    return base


def main() -> int:
    parser = argparse.ArgumentParser(description="Combine one or more CQF benchmark JSON reports into a comparison bundle")
    parser.add_argument("reports", nargs="+", type=Path, help="Path(s) to results/<run_id>.json report files")
    parser.add_argument("--out", type=Path, required=True, help="Output base path without extension, e.g. results/final_compare")
    args = parser.parse_args()

    merged = _merge_reports(args.reports)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out_json = args.out.with_suffix(".json")
    out_md = args.out.with_suffix(".md")
    out_json.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    write_markdown_summary(merged, out_md)
    artifact_paths = write_comparison_bundle(merged, args.out)

    print(f"Wrote merged report JSON: {out_json}")
    print(f"Wrote merged report MD:   {out_md}")
    for artifact_path in artifact_paths:
        print(f"Wrote merged artifact:   {artifact_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
