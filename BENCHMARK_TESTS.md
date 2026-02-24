# Benchmark Test Definitions

This file defines benchmark semantics and scoring rules.

Detailed scenario inventory and intents live in `catalog.md`.

## Suite layout

- Suite file: `bench/scenarios/tpcqf/suite.yaml`
- Scenario folders: `bench/scenarios/tpcqf/<SCENARIO_ID>/`
- Scenario config: `scenario.yaml`
- CQL: `scenario.cql`
- Data config: `data.yaml` (Type 2 only)
- Validation config: `expected.yaml`

## Test classes

## Type 1 (Conformance): `CONF###`

- Purpose: endpoint/verb conformance for CQF REST operations.
- Inputs: `scenario.yaml`, `scenario.cql`, `expected.yaml`.
- No setup data, no FSH, no mutator.
- Scoring:
  - PASS (green): 2xx
  - UNSUPPORTED (gray): 422
  - WARNING (yellow): other 4xx classes indicating server/config attention needed
  - FAIL (red): 5xx and timeout/crash
- Timing: excluded from performance metrics.

## Type 2 (Capability + Performance): `CAP###-P` and `CAP###-I`

- Purpose: data-backed CQL capability and performance checks.
- Inputs: `scenario.yaml`, `scenario.cql`, `data.yaml`, `expected.yaml`, `match.fsh`, `variations.fsh`, `mutator.yaml`.
- `-P`: preload data flow (`setup`) and optional restart before query execution.
- `-I`: inline data flow (bundle in request payload).
- Scoring:
  - PASS: expected HTTP + correctness validators pass.
  - FAIL: error status, unsupported status for that scenario, or correctness mismatch.
- Timing:
  - Recorded only for PASS requests.
  - FAIL requests are excluded from latency percentiles.

## HTTP outcome policy

Each scenario defines `expected_http` in `scenario.yaml`:

- `success`: statuses considered valid for that scenario.
- `unsupported`: statuses treated as unsupported behavior.
- `fail`: explicit failure statuses.

For Type 2 tests, only successful + correct responses count toward timed metrics.

## Selectivity

Default selectivity is `0.2` unless overridden per scenario.

Selectivity is applied by data generation/mutation logic where relevant.

## Reporting

Markdown summary includes both test classes side-by-side across engines:

- Conformance matrix: PASS/FAIL only.
- Capability matrix: PASS/FAIL with timing shown only for PASS rows.
