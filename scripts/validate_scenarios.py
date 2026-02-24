#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from config_io import load_config

REQUIRED_SCENARIO_KEYS = {
    "id",
    "name",
    "test_type",
    "kind",
    "method",
    "path",
    "required_capabilities",
    "expected_http",
    "expected_file",
    "cql_file",
}


def validate_http_policy(policy: Any, context: str, errors: list[str]) -> None:
    if not isinstance(policy, dict):
        errors.append(f"{context}: expected_http must be an object")
        return
    success = policy.get("success")
    unsupported = policy.get("unsupported")
    warning = policy.get("warning")
    if not isinstance(success, list) or not success:
        errors.append(f"{context}: expected_http.success must be a non-empty list")
    if unsupported is not None and not isinstance(unsupported, list):
        errors.append(f"{context}: expected_http.unsupported must be a list")
    if warning is not None and not isinstance(warning, list):
        errors.append(f"{context}: expected_http.warning must be a list")


def validate_scenario_dir(base_dir: Path, scenario_id: str, errors: list[str]) -> None:
    scenario_dir = base_dir / scenario_id
    scenario_file = scenario_dir / "scenario.yaml"
    if not scenario_file.exists():
        errors.append(f"{scenario_id}: missing scenario.yaml")
        return

    scenario = load_config(scenario_file)
    for key in REQUIRED_SCENARIO_KEYS:
        if key not in scenario:
            errors.append(f"{scenario_id}: missing required key '{key}' in scenario.yaml")

    if scenario.get("id") != scenario_id:
        errors.append(f"{scenario_id}: scenario.yaml id mismatch ({scenario.get('id')})")

    validate_http_policy(scenario.get("expected_http"), f"{scenario_id}", errors)

    test_type = str(scenario.get("test_type", "")).lower()

    data_file = scenario.get("data_file")
    if test_type == "capability":
        if not isinstance(data_file, str):
            errors.append(f"{scenario_id}: capability scenario must define data_file")
        else:
            p = scenario_dir / data_file
            if not p.exists():
                errors.append(f"{scenario_id}: missing {data_file}")
            else:
                data_cfg = load_config(p)
                setup = data_cfg.get("setup")
                if isinstance(setup, dict):
                    gen = setup.get("generator")
                    if isinstance(gen, dict) and str(gen.get("type", "")) == "fsh_mutation":
                        for key in ("match_fsh", "variations_fsh", "mutator_file"):
                            val = gen.get(key)
                            if not isinstance(val, str) or not (scenario_dir / val).exists():
                                errors.append(f"{scenario_id}: setup.generator.{key} missing or file not found")

    expected_file = scenario.get("expected_file")
    if isinstance(expected_file, str):
        p = scenario_dir / expected_file
        if not p.exists():
            errors.append(f"{scenario_id}: missing {expected_file}")
        else:
            expected = load_config(p)
            validators = expected.get("validators")
            if validators is not None and not isinstance(validators, list):
                errors.append(f"{scenario_id}: expected validators must be a list")

    cql_file = scenario.get("cql_file")
    if isinstance(cql_file, str):
        p = scenario_dir / cql_file
        if not p.exists():
            errors.append(f"{scenario_id}: missing {cql_file}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate folder-based scenario suite")
    parser.add_argument("--suite", type=Path, default=Path("bench/scenarios/tpcqf/suite.yaml"))
    args = parser.parse_args()

    suite_file = args.suite
    if suite_file.is_dir():
        suite_file = suite_file / "suite.yaml"

    if not suite_file.exists():
        print(f"Suite file not found: {suite_file}")
        return 2

    suite = load_config(suite_file)
    scenario_ids = suite.get("scenario_ids")
    if not isinstance(scenario_ids, list) or not scenario_ids:
        print(f"Invalid suite file {suite_file}: scenario_ids must be a non-empty list")
        return 2

    base_dir = suite_file.parent
    errors: list[str] = []
    validate_http_policy(suite.get("expected_http"), "suite", errors)
    for sid in scenario_ids:
        validate_scenario_dir(base_dir, str(sid), errors)

    # Ensure no orphan scenario folders are silently ignored.
    listed = {str(x) for x in scenario_ids}
    for child in base_dir.iterdir():
        if child.is_dir() and (child / "scenario.yaml").exists() and child.name not in listed:
            errors.append(f"{child.name}: folder exists but is not listed in suite scenario_ids")

    if errors:
        print("Scenario validation failed:")
        for e in errors:
            print(f"- {e}")
        return 1

    print(f"Scenario validation OK: {len(scenario_ids)} scenarios in {suite_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
