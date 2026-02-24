#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from run_benchmark import (  # type: ignore
    EngineAdapter,
    build_patient_ids,
    load_suite_with_scenarios,
    prepare_payload,
    resolve_selectivity,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate per-scenario payload data files outside benchmark execution")
    parser.add_argument("--suite", type=Path, default=Path("bench/scenarios/tpcqf/suite.yaml"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--scale", type=int, required=True)
    parser.add_argument("--selectivity", type=float, default=0.2)
    parser.add_argument("--phase", choices=["setup", "main", "both"], default="setup")
    parser.add_argument("--scenario", action="append", default=[], help="Scenario ID(s) to include")
    args = parser.parse_args()

    suite, scenarios, _ = load_suite_with_scenarios(args.suite)
    defaults = suite.get("defaults", {}) if isinstance(suite.get("defaults", {}), dict) else {}
    patient_ids = build_patient_ids(args.scale)
    selected = set(args.scenario) if args.scenario else None
    adapter = EngineAdapter()

    phases = ["setup", "main"] if args.phase == "both" else [args.phase]

    generated = 0
    for scenario in scenarios:
        sid = str(scenario.get("id", ""))
        if selected is not None and sid not in selected:
            continue

        sel = resolve_selectivity(scenario, defaults, args.selectivity)
        for phase in phases:
            if phase == "setup" and not isinstance(scenario.get("setup"), dict):
                continue

            spec = dict(scenario.get("setup", {})) if phase == "setup" else dict(scenario)
            spec["_data_config"] = scenario.get("_data_config")
            spec["__base_dir"] = scenario.get("__base_dir")

            for patient_id in patient_ids:
                payload = prepare_payload(
                    spec,
                    patient_id,
                    adapter,
                    selectivity=sel,
                    phase=phase,
                    apply_adapter=False,
                )
                if payload is None:
                    continue

                out_file = args.out / sid / phase / f"{patient_id}.json"
                out_file.parent.mkdir(parents=True, exist_ok=True)
                if isinstance(payload, (dict, list)):
                    out_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
                else:
                    out_file.write_text(str(payload), encoding="utf-8")
                generated += 1

    print(f"Generated {generated} payload file(s) in {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
