---
title: Benchmark Suites
description: How suites group scenarios, set defaults, and define HTTP outcome policy.
---

A **suite** is the unit you run. It groups an ordered list of scenarios, sets
shared defaults, and declares a default HTTP outcome policy. The reference suite
is **TPCQF**, defined in `bench/scenarios/tpcqf/suite.yaml`.

## Anatomy of a suite

```yaml
suite_id: TPCQF
description: CQF benchmark split into conformance (CONF###) and capability+performance (CAP###-P/I).
defaults:
  timeout_seconds: 30
  concurrency: 16
  warmup_requests: 10
  requests_per_patient: 1
  selectivity: 0.2
expected_http:
  success: [200, 201]
  unsupported: [400, 404, 405, 409, 410, 415, 422, 501]
  fail: []
scenario_ids:
  - CONF001
  - CONF002
  # ...
  - CAP001-P
  - CAP001-I
  # ...
```

| Field | Meaning |
| --- | --- |
| `suite_id` | Identifier used in the `run_id` and reports. |
| `description` | Free-text summary of the suite. |
| `defaults` | Run defaults applied unless overridden per scenario or by CLI flags. |
| `expected_http` | Default HTTP outcome policy inherited by scenarios that don't define their own. |
| `scenario_ids` | Ordered list of scenario folder names to include. |

## Folder layout

TPCQF uses a folder-based schema. The suite file lists scenario IDs; each ID maps
to a directory under the suite's base directory:

```
bench/scenarios/tpcqf/
  suite.yaml
  CONF010/
    scenario.yaml
    scenario.cql
    expected.yaml
  CAP001-P/
    scenario.yaml
    scenario.cql
    data.yaml
    expected.yaml
    match.fsh
    variations.fsh
    mutator.yaml
  ...
```

Conformance scenarios need only `scenario.yaml`, `scenario.cql`, and
`expected.yaml`. Data-backed capability scenarios add `data.yaml` and the FSH +
mutator fixtures. See [Test Cases](/cqf-bench/concepts/test-cases/) for the
per-scenario detail.

## Defaults

`defaults` provides run-wide knobs:

- `timeout_seconds` — per-request timeout.
- `concurrency` — number of concurrent requests when executing a scenario across
  patients.
- `warmup_requests` — warmup requests issued before timing.
- `requests_per_patient` — requests issued per synthetic patient.
- `selectivity` — default match fraction for data generation.

CLI flags (`--timeout`, `--concurrency`, `--selectivity`) override suite defaults
at run time; a scenario's own fields override the suite for that scenario.

## HTTP outcome policy

`expected_http` classifies status codes into outcome buckets:

| Bucket | Meaning |
| --- | --- |
| `success` | Statuses considered valid (PASS) for the scenario. |
| `unsupported` | Statuses treated as "engine does not support this" (gray). |
| `warning` | Other statuses that signal server/config attention (yellow). |
| `fail` | Explicit failure statuses (red); anything unclassified also fails. |

A scenario may define its own `expected_http`; otherwise it inherits the suite's.
Running with `--score-mode strict-2xx` ignores these policies and requires `2xx`
for both setup and main calls.

## Validating a suite

Before running, confirm the suite is well-formed:

```bash
python scripts/validate_scenarios.py --suite bench/scenarios/tpcqf/suite.yaml
```

The validator checks that every listed scenario folder exists and is structurally
valid, that the HTTP policy is well-formed, and — importantly — that no scenario
folder exists on disk without being listed in `scenario_ids` (no silently ignored
orphans).

## Other suites

The repository also includes focused suites such as
`bench/scenarios/library_write_once_execute_many.yaml`, which writes a library
once and then evaluates it repeatedly to measure steady-state `$evaluate`
throughput. You can author your own suite by creating a `suite.yaml` and the
scenario folders it references. See [Contributing](/cqf-bench/contributing/).
