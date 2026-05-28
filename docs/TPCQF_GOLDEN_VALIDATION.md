# TPCQF Golden Validation Design

**Status:** Implemented (2026-05-28)  
**Audience:** Adversarial code review, scenario authors, engine integrators  
**Suite:** `bench/scenarios/tpcqf/` (TPCQF)

This document specifies how CAP (capability + performance) scenarios prove **correct CQL semantics**, not only HTTP success. It is the design record for the TPC-H-style hardening pass.

---

## Goals

1. **Falsifiable correctness** — A wrong count, boolean, or list length must **FAIL** validators, not PASS with timing credit.
2. **Deterministic golden answers** — Expected results derive from `mutator.yaml` (`total_count`, selectivity, scenario-specific overlays), not hand-waved constants in prose.
3. **Orthogonal fixtures** — Scenarios that claim to test different CQL constructs must not collapse to the same numeric answer because of shared data bugs.
4. **Clear CONF boundary** — Type 1 tests prove **endpoint/verb** behavior only; they do not validate clinical or CQL outcomes.

---

## Non-goals

- Certification of engines against the CQF IG (conformance ≠ certification).
- Cross-patient aggregation (all CAP CQL uses `context Patient`; golden values are **per patient**).
- Validating engine-specific JSON shapes beyond paths documented below (adapters may normalize).

---

## Architecture

```text
mutator.yaml + match.fsh + variations.fsh
        │
        ▼
generate_bundle_from_fsh_mutator()  ──► resident / inline data
        │
        ▼
$evaluate (Library + expression)
        │
        ▼
run_response_validators(expected.yaml, validation_context)
        │
        ├── PASS + timed  (HTTP 200 + validators OK)
        └── FAIL          (wrong semantics; no timing credit)
```

### `validation_context` (harness)

Built in `run_scenario()` from:

| Key | Source | Use in expressions |
| --- | --- | --- |
| `selectivity` | scenario or suite default | `round(total_count * selectivity)` |
| `total_count` | `mutator.yaml` | `total_count`, list lengths |
| `match_count` | computed mix | `match_count` (alias) |
| `nomatch_count` | computed mix | diagnostics |
| `null_id_count` | `fixed_templates` in mutator | CAP011: `total_count - null_id_count` |
| `scale_factor` | len(patient_ids) | future multi-patient checks |
| `requests_per_patient` | run config | future |
| `repetitions` | run config | future |

Expressions are evaluated by `tokenized_numeric_equals` (safe AST subset in `run_benchmark.py`).

### Standard validator stack

All CAP scenarios include:

```yaml
validators:
  - type: not_operation_outcome_error
  # scenario-specific validators below
```

Numeric counts use:

```yaml
  - type: tokenized_numeric_equals
    path: $.parameter[*]
    expression: <see per-scenario table>
    expected_type: valueInteger
    rounding: nearest
```

`path: $.parameter[*]` selects each `parameter` object; the validator finds a `valueInteger` on any matching node (expression name varies by engine).

---

## Per-scenario golden answers (per patient)

Assumptions unless noted:

- `total_count: 40` (default mutator)
- `selectivity: 0.2` → `match_count = 8`, `nomatch_count = 32` (last mix slot absorbs rounding remainder)
- Patient-scoped evaluation

| Scenario | CQL construct | Golden expression | Notes |
| --- | --- | --- | --- |
| CAP001-P/I | `Count([Condition])` | `total_count` | Baseline volume (40) |
| CAP002-P/I | Valueset retrieve | `round(total_count * selectivity)` | 8 |
| CAP003-P/I | VS in `where` | `round(total_count * selectivity)` | Must equal CAP002; see equivalence |
| CAP004-P/I | `return` list | `min_items` 40 on list parts | See response shape |
| CAP005-P/I | Tuple + define | `round(total_count * selectivity)` | 8 |
| CAP006-P/I | `with` semi-join | `round(total_count * selectivity)` | **Fixture:** no obs linked to `ConditionNoMatch` |
| CAP007-P/I | `without` anti-join | `round(total_count * selectivity)` | 8 with default linked obs |
| CAP008-P/I | `sort by id` | 40 parts + `response_regex` order | m-* before n-* in body |
| CAP009-P/I | Complex predicate | `round(total_count * selectivity)` | 8 |
| CAP010-P/I | `exists` | `valueBoolean: true` | `selectivity: 0.5` → 20 matches (stress) |
| CAP011-P/I | `let` + null filter | `total_count - null_id_count` | `null_id_count: 2` fixed resources |

---

## Fixture overlays (orthogonality)

### Shared baseline

Most CAP scenarios share `match.fsh` + `variations.fsh` + default `mutator.yaml` under each folder (copied or symlinked by convention — currently duplicated per folder in repo).

### CAP006 — semi-join isolation

**Problem:** Shared `linked_templates` attached `ObservationCancelled` (code `90000001`) to `ConditionNoMatch`, so `with O where O.code ~ C.code` matched every condition → count 40 (same as CAP001).

**Fix:** `CAP006-P` and `CAP006-I` use a **local `mutator.yaml`** with:

```yaml
linked_templates:
  ConditionMatch:
    - ObservationFinal
  # ConditionNoMatch: intentionally no linked observations
```

Expected join count = **8** (only match rows have a related obs).

### CAP011 — `let` is not a no-op

**Problem:** All conditions had `id`; `where CId is not null` filtered nothing.

**Fix:** Local `variations.fsh` adds `ConditionMissingId` (no `id`). Local `mutator.yaml`:

```yaml
fixed_templates:
  - template: ConditionMissingId
    count: 2
```

Resources are **in addition to** the 40 mix conditions. Golden count = **38**.

---

## CAP002 vs CAP003 equivalence

| Aspect | CAP002 | CAP003 |
| --- | --- | --- |
| Surface | `[Condition: "VS"]` | `[Condition] where code in VS` |
| Golden | `round(total_count * selectivity)` | same |

**Review checklist:** On a correct engine, counts must match for the same patient data. The harness does not auto-compare paired scenarios in one run; reviewers should:

1. Run both with identical `--scale`, `--selectivity`, and data root.
2. Compare JSON reports or Markdown matrices.

Future work: paired-equivalence validator across two scenario IDs in one run.

---

## CAP004 / CAP008 response shapes

Engines may return list results as:

- `parameter[].part[].valueString` (preferred path in validators), or
- other nested shapes.

Validators use expression-named `part` arrays where possible. If an engine fails only `min_items` on `part`, inspect raw `Parameters` and extend paths in a **product-specific** overlay (same pattern as engine adapters).

### CAP008 sort check

CQL uses `sort by id.value` (not `resourceType` — all ties previously).

`response_regex` on the raw response body asserts `cond-…-m-0` appears before `cond-…-n-0`, consistent with lexicographic id order for generated ids.

---

## Type 1: CONF### scope

CONF scenarios use trivial CQL (`define "ConformanceTrue": true`) and **empty or HTTP-only validators**.

| CONF tests | Does not test |
| --- | --- |
| Route exists | Correct clinical result |
| Verb allowed | Expression evaluation semantics |
| CQF-shaped status | Data preload |

Catalog **Audit Status** for CONF means wire-level review, not golden CQL outcomes.

Future tier (not in this pass): **CONF-EVAL** with minimal real expressions and shared golden validators.

---

## Validator types used

| Type | Purpose in TPCQF |
| --- | --- |
| `not_operation_outcome_error` | No fatal / evaluation error text |
| `tokenized_numeric_equals` | Count() results |
| `value_type_and_equals` | `exists` → boolean `true` |
| `min_items` | List length (CAP004, CAP008) |
| `response_regex` | CAP008 ordering smoke test |

See `docs-site` configuration reference for full schema.

---

## Adversarial review checklist

Use this list when challenging a PR that touches scenarios or validators.

### Data

- [ ] Does `mutator.yaml` `total_count` match golden expressions?
- [ ] Does selectivity flow from scenario → generator → `validation_context`?
- [ ] Do scenario-specific overlays (CAP006, CAP011) remain local without breaking CAP007?
- [ ] Are `linked_templates` intentional for anti-join tests (CAP007)?

### CQL

- [ ] Does `cql_entrypoint` match `scenario.yaml` `query.expression`?
- [ ] Could a no-op expression PASS (e.g. `Count` on empty set vs full set)?
- [ ] Are CAP002 and CAP003 logically equivalent on paper?

### Validators

- [ ] Is `when_status_in` only `[200]` for timed CAP runs?
- [ ] Can a wrong integer still pass (e.g. missing `tokenized_numeric_equals`)?
- [ ] Are list paths verified against a captured golden `Parameters` sample from HAPI CQF Ruler?

### Harness

- [ ] Is `validation_context.total_count` loaded from the same mutator file as data generation?
- [ ] Does `round(total_count * selectivity)` match mutator mix rounding?

### Catalog honesty

- [ ] Does `catalog.md` Intent column state the **golden formula**?
- [ ] Is CONF marked as wire-only where applicable?

---

## Change log

| Date | Change |
| --- | --- |
| 2026-05-28 | Initial golden validation pass: validators, CAP006/CAP011 fixtures, CAP008/010 fixes, harness context |

---

## References

- `catalog.md` — scenario intents and audit status
- `BENCHMARK_TESTS.md` — scoring and timing rules
- `scripts/run_benchmark.py` — `run_response_validators`, `build_validation_context`
- `scripts/validate_scenarios.py` — structural suite validation
- `tests/test_golden_validation.py` — unit tests for mix counts and validators
