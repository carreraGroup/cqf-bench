#!/usr/bin/env python
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Load one generated dataset into target engine(s) (libraries, measures, valuesets, then one merged resident preload bundle per patient)",
    )
    parser.add_argument("--engines", type=Path, default=Path("bench/config/local.engines.yaml"))
    parser.add_argument(
        "--suite",
        type=Path,
        default=None,
        help="Optional; if omitted, suite path is read from dataset.json under --generated-data-root",
    )
    parser.add_argument(
        "--scale",
        type=int,
        default=None,
        help="Optional; if omitted, scale is read from dataset.json under --generated-data-root",
    )
    parser.add_argument("--generated-data-root", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=None)
    parser.add_argument("--selectivity", type=float, default=0.2)
    parser.add_argument("--filter-engine", action="append", default=[])
    parser.add_argument("--score-mode", choices=["compat", "strict-2xx"], default="compat")
    args = parser.parse_args()

    cmd = [
        sys.executable,
        str(Path(__file__).with_name("run_benchmark.py")),
        "--engines",
        str(args.engines),
        "--generated-data-root",
        str(args.generated_data_root),
        "--run-phase",
        "load",
        "--selectivity",
        str(args.selectivity),
        "--score-mode",
        args.score_mode,
    ]
    if args.suite is not None:
        cmd.extend(["--suite", str(args.suite)])
    if args.scale is not None:
        cmd.extend(["--scale", str(args.scale)])
    if args.timeout is not None:
        cmd.extend(["--timeout", str(args.timeout)])
    for engine_name in args.filter_engine:
        cmd.extend(["--filter-engine", engine_name])
    return subprocess.run(cmd, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
