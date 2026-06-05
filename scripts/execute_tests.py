#!/usr/bin/env python
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Execute CQF benchmark queries without setup load; uses pre-generated inline payloads when provided"
    )
    parser.add_argument("--engines", type=Path, default=Path("bench/config/local.engines.yaml"))
    parser.add_argument("--suite", type=Path, default=Path("bench/scenarios/tpcqf/suite.yaml"))
    parser.add_argument("--scale", type=int, required=True)
    parser.add_argument("--out", type=Path, default=Path("results"))
    parser.add_argument("--generated-data-root", type=Path, default=None)
    parser.add_argument("--runs", type=int, default=5, help="Number of repeated scenario runs (averaged in timing)")
    parser.add_argument("--concurrency", type=int, default=None)
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
        "--suite",
        str(args.suite),
        "--scale",
        str(args.scale),
        "--out",
        str(args.out),
        "--run-phase",
        "execute",
        "--selectivity",
        str(args.selectivity),
        "--score-mode",
        args.score_mode,
        "--repetitions",
        str(max(1, int(args.runs))),
    ]
    if args.generated_data_root is not None:
        cmd.extend(["--generated-data-root", str(args.generated_data_root)])
    if args.concurrency is not None:
        cmd.extend(["--concurrency", str(args.concurrency)])
    if args.timeout is not None:
        cmd.extend(["--timeout", str(args.timeout)])
    for engine_name in args.filter_engine:
        cmd.extend(["--filter-engine", engine_name])
    return subprocess.run(cmd, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
