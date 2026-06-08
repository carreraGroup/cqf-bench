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

**CQL and golden validation:** CONF scenarios use a trivial expression
(`define "ConformanceTrue": true`) to exercise the `$evaluate` path where
applicable. They do **not** assert clinical or numeric correctness — only that the
route responds with an expected HTTP class. See
[Golden Validation](/cqf-bench/concepts/golden-validation/) for what “correct
answer” checking means on capability rows.

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

- `PASS` — expected HTTP outcome **and** all **golden validators** in
  `expected.yaml` pass (see [Golden Validation](/cqf-bench/concepts/golden-validation/)).
- `FAIL` — error status, an unsupported status for that scenario, or a
  correctness mismatch (wrong count, boolean, list length, etc., even when HTTP is
  `200`).

**Timing:** recorded **only** for PASS requests. Failed requests are excluded from
latency percentiles. A fast wrong answer never receives a latency number.

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

## Golden validation (`expected.yaml`)

Capability scenarios use **golden validation**: the harness compares the
engine's `$evaluate` result to an expected answer derived from the scenario's data
generator settings (`total_count`, `selectivity`, and any scenario-specific mutator
overlays).

Validators run only when the response status is in `when_status_in` (typically
`[200]`). Example for an unfiltered count scenario:

```yaml
when_status_in: [200]
validators:
  - type: not_operation_outcome_error
  - type: tokenized_numeric_equals
    path: $.parameter[*]
    expression: total_count
    expected_type: valueInteger
    rounding: nearest
```

Here `total_count` comes from `mutator.yaml` (default **40** per patient). An
engine that returns `200` with `valueInteger: 7` fails as **incorrect result**.

Expression names available in `tokenized_numeric_equals` include `total_count`,
`selectivity`, `match_count`, `nomatch_count`, and `null_id_count` (when the mutator
defines `fixed_templates`). The harness also allows `round(total_count * selectivity)`
for filtered counts.

Validator types used across the CAP catalog:

| Type | Role |
| --- | --- |
| `not_operation_outcome_error` | No fatal `OperationOutcome` or evaluation-error parameter. |
| `tokenized_numeric_equals` | Integer results (`Count`, etc.) match a context expression. |
| `value_type_and_equals` | Booleans, strings, and other typed values (e.g. `exists` → `true`). |
| `min_items` | List results expose at least `min` elements (e.g. `return` projections). |
| `response_regex` | Serialized body matches a pattern (e.g. sort order). |
| `parameters_has_name` | A named `Parameters.parameter` is present. |
| `define_present` | A named define appears in the output. |
| `function_result_body_equals` | A result parameter body matches an expected structure. |

Per-scenario golden expectations (fixture overlays, equivalence pairs, list paths)
are documented in the [Scenario Catalog](/cqf-bench/reference/scenario-catalog/).

See [Golden Validation](/cqf-bench/concepts/golden-validation/) for the full model
and [Configuration Reference](/cqf-bench/reference/configuration/) for the
`expected.yaml` schema.

## Data generation (Type 2 only)

Type 2 scenarios generate FHIR data deterministically from FSH templates and a
mutator:

- `match.fsh` — the canonical "matching" fixtures.
- `variations.fsh` — non-matching / variant fixtures.
- `mutator.yaml` — the selectivity mix, per-template mutations, linked resources,
  optional `fixed_templates`, and uniqueness constraints, all driven by a stable
  per-patient seed.

This makes the same scale produce the same data on every run, so **golden answers**
are reproducible. Scenario-specific mutator files (for example CAP006 semi-join or
CAP011 `let`) adjust linked resources or add extra templates without changing the
CQL. See [Configuration Reference](/cqf-bench/reference/configuration/) for the
mutator schema.

## Skipping vs. failing

If an engine does not declare a scenario's `required_capabilities`, the scenario
is **skipped** for that engine (reported as skipped, not failed). This keeps the
matrix honest: an engine isn't penalized for an operation class it never claimed
to support.
