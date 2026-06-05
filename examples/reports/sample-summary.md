# CQF Benchmark Report: TPCQF-v1_100_sample00

> **Illustrative sample — not a real benchmark run.** Hand-authored to demonstrate
> the report format and status semantics. Not official results for any engine.

- suite: `TPCQF-v1`
- scale: `100`
- concurrency: `16`
- started_utc: `2026-06-04T15:00:00+00:00`
- started_local: `2026-06-04T11:00:00-04:00`
- ended_utc: `2026-06-04T15:03:42+00:00`
- ended_local: `2026-06-04T11:03:42-04:00`
- duration_seconds: `222.41`
- score_mode: `compat`
- repetitions: `5`

**Status legend:**

- `PASS` — scenario executed and returned the expected result.
- `FAIL` — scenario executed but was incorrect, errored, timed out, or returned a warning status.
- `UNSUPPORTED` — the engine does not support the capability this scenario requires.
- `NOT_RUN` — scenario was not executed for this engine (e.g., filtered out or skipped); not a correctness failure.

Timing is shown only for `PASS` results, so performance is never compared across incorrect responses.

## Conformance Matrix

| Scenario | Intent | hapi-cqf-ruler-local Result | hapi-cqf-ruler-local Time | hapi-cqf-ruler-local Note |
| --- | --- | --- | --- | --- |
| CONF001 | CapabilityStatement advertises CQF operations | PASS |  |  |
| CONF002 | $cql system-level evaluation endpoint shape | PASS |  | endpoint: POST /fhir/$cql |
| CONF003 | Library $evaluate endpoint shape | PASS |  | endpoint: POST /fhir/Library/$evaluate |
| CONF004 | $apply (PlanDefinition) endpoint shape | UNSUPPORTED |  | unsupported; HTTP 501 |

## Capability + Performance Matrix

| Scenario | Intent | hapi-cqf-ruler-local Result | hapi-cqf-ruler-local Time | hapi-cqf-ruler-local Note |
| --- | --- | --- | --- | --- |
| CAP001-P | Resident data load + measure $evaluate (preloaded) | PASS | 84.2ms | endpoint: POST /fhir/Measure/$evaluate-measure; HTTP 200 |
| CAP001-I | Same measure with inline bundle | PASS | 131.7ms | endpoint: POST /fhir/$cql; HTTP 200 |
| CAP002-P | Multi-library compute (preloaded) | FAIL |  | incorrect result; expected 42 members, got 37; HTTP 200 |
| CAP003-P | write-once-execute-many library reuse | UNSUPPORTED |  | unsupported=5; HTTP 422 |
| CAP004-P | $apply care plan generation (preloaded) | NOT_RUN |  | not executed for this engine |
