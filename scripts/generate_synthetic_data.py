#!/usr/bin/env python
"""Generate synthetic FHIR-ish benchmark data at different magnitudes.

Outputs:
- patients.ndjson: one Patient resource per line
- observations.ndjson: one Observation resource per patient

Notes:
- `--patients` (or `--scale`) controls patient count and aligns with benchmark `--scale`.
- `--selectivity` controls matching/non-matching Observation ratio (default 20% match).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def clamp_selectivity(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def patient_resource(pid: str) -> dict:
    return {
        "resourceType": "Patient",
        "id": pid,
        "name": [{"family": f"Family{pid}", "given": [f"Given{pid}"]}],
        "gender": "unknown",
    }


def observation_resource(pid: str, matching: bool) -> dict:
    code = "4548-4" if matching else "39156-5"
    value = 7.2 if matching else 5.4
    return {
        "resourceType": "Observation",
        "id": f"obs-{pid}",
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": code}]},
        "subject": {"reference": f"Patient/{pid}"},
        "valueQuantity": {"value": value, "unit": "%"},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate synthetic benchmark data")
    parser.add_argument("--patients", type=int, default=None, help="Number of patients")
    parser.add_argument("--scale", type=int, default=None, help="Alias for --patients (benchmark-aligned scale)")
    parser.add_argument(
        "--selectivity",
        type=float,
        default=0.2,
        help="Fraction of generated resources marked as matching (0.0-1.0). Default 20%.",
    )
    parser.add_argument("--out", type=Path, required=True, help="Output directory")
    args = parser.parse_args()

    if args.patients is None and args.scale is None:
        parser.error("one of --patients or --scale is required")
    if args.patients is not None and args.scale is not None and args.patients != args.scale:
        parser.error("--patients and --scale must match when both are provided")
    patients = args.patients if args.patients is not None else args.scale
    assert patients is not None
    selectivity = clamp_selectivity(args.selectivity)
    matching_count = int(round(patients * selectivity))

    args.out.mkdir(parents=True, exist_ok=True)
    patients_file = args.out / "patients.ndjson"
    observations_file = args.out / "observations.ndjson"

    with patients_file.open("w", encoding="utf-8") as pf, observations_file.open("w", encoding="utf-8") as of:
        for i in range(1, patients + 1):
            pid = str(i)
            pf.write(json.dumps(patient_resource(pid)) + "\n")
            of.write(json.dumps(observation_resource(pid, matching=(i <= matching_count))) + "\n")

    print(
        f"Generated {patients} patients into {args.out} "
        f"(matching observations: {matching_count}/{patients}, selectivity={selectivity:.3f})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
