#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from run_benchmark import generate_scenario_payload_files  # type: ignore


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate the full suite shared corpus tree (starter metadata, merged resident bundles, compiled inline payloads)",
    )
    parser.add_argument(
        "--suite",
        type=Path,
        default=None,
        help="Deprecated: ignored. Generation always uses the built-in benchmark suite.",
    )
    parser.add_argument("--out", type=Path, required=True, help="Output root (same as --generated-data-root for generate)")
    parser.add_argument("--scale", type=int, required=True)
    parser.add_argument("--selectivity", type=float, default=0.2)
    args = parser.parse_args()

    if args.suite is not None:
        print("generate_scenario_data.py: --suite is deprecated and ignored.", file=sys.stderr)
    return generate_scenario_payload_files(
        args.out,
        args.scale,
        args.selectivity,
    )


if __name__ == "__main__":
    raise SystemExit(main())
