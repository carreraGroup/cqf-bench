---
title: Test Cases
description: The two scenario classes — conformance and capability+performance — and how each is defined and scored.
---

A **test case** (scenario) is a single check. Each scenario lives in its own
folder and is one of two classes.

:::tip
For the full, scenario-by-scenario list of what every check is intended to test —
all `CONF###` spec-conformance checks and all `CAP###` engine stress probes — see
the [Scenario Catalog](/cqf-bench/reference/scenario-catalog/).
:::

## Type 1 — Conformance (`CONF###`)

**Purpose:** verify that an engine's CQF REST operation/verb is reachable and
returns a CQF-conformant status code. These are untimed red/green checks.

**Inputs:** `scenario.yaml`, `scenario.cql`, `expected.yaml`. No setup data, no
FSH, no mutator.

**Scoring (by HTTP class):**

| Outcome | Status | Meaning |
| --- | --- | --- |
| `PASS` (green) | 2xx | Endpoint/verb reachable and conformant. |
| `UNSUPPORTED` (gray) | 422 | Operation not supported by this engine. |
| `WARNING` (yellow) | other 4xx | Server/config attention may be needed. |
| `FAIL` (red) | 5xx, timeout, crash | Not conformant. |

**Timing:** excluded from performance metrics entirely.

Example `scenario.yaml`:

```yaml
id: CONF010
name: GET /Library/$evaluate conformance
test_type: conformance
kind: fetch
method: GET
path: /Library/$evaluate
required_capabilities: []
expected_http:
  success: [200, 201, 202, 204]
  unsupported: [422]
  warning: [400, 401, 403, 404, 405, 406, 409, 410, 412, 415, 429]
  fail: [500, 501, 502, 503, 504]
expected_file: expected.yaml
cql_file: scenario.cql
cql_entrypoint: ConformanceTrue
query:
  library: Library/BenchCONF010|1.0.0
  subject: Patient/{patient_id}
  expression: ConformanceTrue
```

The CONF catalog covers the CQF operation families across verbs and instance vs.
type-level forms — `/metadata`, `/$cql`, `Library/$evaluate`,
`Library/$data-requirements`, `Measure/$evaluate-measure`, `Measure/$care-gaps`,
`Measure/$collect-data`, `Measure/$submit-data`, `PlanDefinition/$apply`,
`PlanDefinition/$package`, `ActivityDefinition/$apply`, and more.

## Type 2 — Capability + Performance (`CAP###-P` / `CAP###-I`)

**Purpose:** data-backed CQL capability and performance. Does the CQL produce the
correct result, and how fast?

**Variants:**

- **`-P` (Preload):** setup data is loaded into the server first (resident data),
  optionally restarting the engine before execution.
- **`-I` (Inline):** data is sent in the request payload as a bundle.

**Inputs:** `scenario.yaml`, `scenario.cql`, `data.yaml`, `expected.yaml`, plus
the fixture set `match.fsh`, `variations.fsh`, `mutator.yaml`.

**Scoring:**

- `PASS` — expected HTTP outcome **and** all correctness validators pass.
- `FAIL` — error status, an unsupported status for that scenario, or a
  correctness mismatch.

**Timing:** recorded **only** for PASS requests. Failed requests are excluded from
latency percentiles.

Example `scenario.yaml` (preload variant):

```yaml
id: CAP001-P
name: Count retrieve all of one resource (preload)
test_type: capability
kind: compute
method: GET
path: /Library/$evaluate
query:
  library: Library/BenchCAP001-P|1.0.0
  subject: Patient/{patient_id}
  expression: CountAllCondition
required_capabilities:
  - resident_data_load
  - resident_execute
selectivity: 0.2
expected_http:
  success: [200]
  unsupported: [400, 405, 415, 422, 501]
  fail: []
expected_file: expected.yaml
data_file: data.yaml
cql_file: scenario.cql
cql_entrypoint: CountAllCondition
setup:
  method: POST
  path_role: data
  path: /Bundle
  per_patient: true
  expected_http:
    success: [200, 201]
    unsupported: [400, 422]
    fail: []
restart_after_setup: true
```

The CAP catalog exercises representative CQL constructs: counting retrieves,
valueset retrieves and predicates, return projections, tuples populated from
other defines, `with` / `without` join clauses, sorts, complex predicates with
function calls, `exists`, and `let` expressions — each in both preload and inline
variants.

## CQL and entrypoints

Each scenario references a CQL file via `cql_file` and names the define to
evaluate via `cql_entrypoint`. For `Library/$evaluate` scenarios, the harness
wires the library reference and subject into the query automatically and submits
the CQL as a `Library` resource during the load phase.

## Correctness validators

Correctness is asserted in `expected.yaml`. Validators only run when the response
status is in `when_status_in`. Example:

```yaml
when_status_in: [200]
validators:
  - type: not_operation_outcome_error
  - type: min_items
    path: $.parameter[*]
    min: 1
```

Validator types include (among others):

| Type | Checks |
| --- | --- |
| `not_operation_outcome_error` | Response has no error/fatal `OperationOutcome` and no "evaluation error". |
| `parameters_has_name` | A `Parameters.parameter` with the given `name` exists. |
| `define_present` | A named define is present in the output. |
| `min_items` | A JSON path selects at least `min` nodes. |
| `value_type_and_equals` | A node matches an expected FHIR value type (and optional value). |
| `function_result_body_equals` | A named result parameter's body equals the expected body. |
| `tokenized_numeric_equals` | A numeric result equals an expression over run context (e.g. selectivity × scale). |

See the [Configuration Reference](/cqf-bench/reference/configuration/) for the
full validator catalog and `expected.yaml` schema.

## Data generation (Type 2 only)

Type 2 scenarios generate FHIR data deterministically from FSH templates and a
mutator:

- `match.fsh` — the canonical "matching" fixtures.
- `variations.fsh` — non-matching / variant fixtures.
- `mutator.yaml` — the selectivity mix, per-template mutations, linked resources,
  and uniqueness constraints, all driven by a stable per-patient seed.

This makes the same scale produce the same data on every run, so result counts —
and therefore correctness assertions — are reproducible. See
[Configuration Reference](/cqf-bench/reference/configuration/) for the mutator
schema.

## Skipping vs. failing

If an engine does not declare a scenario's `required_capabilities`, the scenario
is **skipped** for that engine (reported as skipped, not failed). This keeps the
matrix honest: an engine isn't penalized for an operation class it never claimed
to support.
