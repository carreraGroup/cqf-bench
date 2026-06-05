---
title: Golden Validation
description: How CQF Bench proves CQL results are correct — not just that the HTTP call succeeded.
---

**Golden validation** is CQF Bench's name for asserting the **expected answer** of a
capability scenario, not only that the server returned HTTP 200.

A timed **PASS** on a `CAP###` row requires:

1. An HTTP status in the scenario's `success` policy (usually `200`), and  
2. Every validator in `expected.yaml` passing on the response body.

If the engine returns `200` with the wrong count, boolean, or list length, the row is
**FAIL** with an **incorrect result** note — and **no latency is recorded** for that
request. Performance numbers are only meaningful when the answer is right.

This is the same idea as benchmark suites like TPC-H: fixed data, a known correct
result, and a scoring rule that rejects wrong answers.

## How the golden answer is derived

Capability scenarios generate synthetic FHIR data per patient from:

- `match.fsh` and `variations.fsh` (templates),
- `mutator.yaml` (`total_count`, selectivity mix, linked resources, optional overlays).

With the default mutator (`total_count: 40`, selectivity `0.2`):

| Slice | Per patient | Role |
| --- | --- | --- |
| `ConditionMatch` | 8 | In valueset `38341003`, active, 2024 date |
| `ConditionNoMatch` | 32 | Out of valueset / inactive / older date |
| Linked observations | 8 + 32 | Final obs on match rows; cancelled obs on nomatch rows (where configured) |

CQL runs in **`context Patient`**, so counts and booleans in validators are
**per patient**, not totals across the whole server.

The harness builds a **validation context** at run time and passes it to validators:

| Context field | Meaning |
| --- | --- |
| `total_count` | From `mutator.yaml` (default 40) |
| `selectivity` | From scenario or suite (default 0.2) |
| `match_count` / `nomatch_count` | From the mutator mix (default 8 / 32) |
| `null_id_count` | From `fixed_templates` when present (CAP011) |

Validators can reference these names in expressions, for example
`round(total_count * selectivity)` or `total_count - null_id_count`.

## Standard validator stack

Every capability scenario includes:

```yaml
- type: not_operation_outcome_error
```

Then scenario-specific checks, commonly:

| Validator | Used for |
| --- | --- |
| `tokenized_numeric_equals` | `Count()` and other integer results |
| `value_type_and_equals` | `exists` → `valueBoolean: true` |
| `min_items` | List projections (`return`) with `part` arrays |
| `response_regex` | Sort-order checks on serialized output (CAP008) |

See [Configuration Reference](/cqf-bench/reference/configuration/) for the full
schema and [Test Cases](/cqf-bench/concepts/test-cases/) for how this fits scoring.

## Scenario-specific fixtures

Most CAP scenarios share the same baseline templates. A few scenarios use **local
mutator or FSH overlays** so the data matches what the CQL is meant to stress:

| Scenario | Overlay | Why it matters |
| --- | --- | --- |
| CAP006 | No observation linked to `ConditionNoMatch` | Semi-join only counts conditions with a related obs (8, not 40) |
| CAP007 | Default links (cancelled obs on nomatch) | Anti-join excludes nomatch rows (8) |
| CAP011 | Two extra conditions without `id` | `let` + `where id is not null` yields 38, not 40 |
| CAP010 | `selectivity: 0.5` on the scenario | More matching rows for `exists` stress (20 vs 8) |

Details for each probe are in the [Scenario Catalog](/cqf-bench/reference/scenario-catalog/).

## What golden validation does not cover

- **Conformance (`CONF###`)** — wire-level HTTP checks only; CQL is trivial
  (`ConformanceTrue`). See [Test Cases](/cqf-bench/concepts/test-cases/#type-1--conformance-conf).
- **Cross-engine JSON shape differences** — validators target common `$evaluate`
  `Parameters` patterns; engine adapters may normalize responses.
- **Certification** — golden validation is a reproducible measurement harness, not
  an official CQF conformance certificate.

Maintainers extending validators or scenarios can read
[`docs/TPCQF_GOLDEN_VALIDATION.md`](https://github.com/carreraGroup/cqf-bench/blob/master/docs/TPCQF_GOLDEN_VALIDATION.md)
in the repository for the full design record and review checklist.

## Related

- [Test Cases](/cqf-bench/concepts/test-cases/) — scenario classes and `expected.yaml`
- [Scenario Catalog](/cqf-bench/reference/scenario-catalog/) — per-scenario golden expectations
- [Results](/cqf-bench/concepts/results/) — incorrect-result failures in reports
