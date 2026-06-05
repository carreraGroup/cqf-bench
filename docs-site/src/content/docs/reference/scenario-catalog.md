---
title: Scenario Catalog
description: Every CQF Bench scenario and what it is intended to test — spec conformance checks and engine stress probes.
---

This is the exhaustive list of scenarios in the reference **TPCQF** suite, with
what each one is intended to test. Scenarios fall into two intents:

- **Conformance (`CONF###`) — CQF specification capabilities.** Does the engine
  implement a given CQF / Clinical Reasoning operation, over a given verb and
  addressing form (type-level vs. instance-level), and return a CQF-conformant
  status code? These are untimed PASS / UNSUPPORTED / WARNING / FAIL checks.
- **Capability + Performance (`CAP###`) — engine stress probes.** Each one
  isolates a single CQL construct and exercises it against deterministically
  generated data, to see whether the engine evaluates it *correctly* and *how
  hard it has to work* as data scales. Timed only on correct responses.

For the scoring rules behind these, see [Test Cases](/cqf-bench/concepts/test-cases/),
[Golden Validation](/cqf-bench/concepts/golden-validation/), and
[Results](/cqf-bench/concepts/results/). The editable source of truth for
intent and audit status is `catalog.md` in the repository root.

## Reading this catalog

- **Variants.** Each capability scenario ships as two variants that share
  identical CQL but differ in how data reaches the engine:
  `-P` (**Preload** — data loaded into the server as resident data, with an
  optional restart before timed execution) and `-I` (**Inline** — data sent in
  the request payload as a bundle). Comparing `-P` vs. `-I` for the same logic
  shows how an engine's resident-data path compares to its inline-data path.
- **Selectivity.** Capability scenarios target a selectivity of `0.2`, so where a
  filter applies, roughly 20% of generated resources match. This keeps result
  counts predictable so correctness can be asserted. Unfiltered scenarios (count
  / return all) still run over the full generated set.
- **Fixtures.** Data is generated from each scenario's `match.fsh` /
  `variations.fsh` templates and `mutator.yaml`, producing `Condition` resources
  (matching and non-matching) plus linked `Observation` resources and a standard
  `Patient` and `ValueSet`. A few scenarios add a **local `mutator.yaml`** or
  **`fixed_templates`** so the data matches what the CQL is meant to stress.
- **Golden validation.** Each `CAP###` row asserts the **expected answer** in
  `expected.yaml` (counts, booleans, list length, sort order). HTTP `200` with a
  wrong answer is **FAIL** / incorrect result — not timed. See
  [Golden Validation](/cqf-bench/concepts/golden-validation/).

---

## Conformance scenarios (`CONF###`)

These verify the engine's CQF REST surface. For each operation, CQF Bench checks
the verbs and addressing forms the IG defines — type-level (`/Resource/$op`) and
instance-level (`/Resource/{id}/$op`), via `GET` and/or `POST`. A `PASS` means the
endpoint is reachable and returns a conformant status; `422` is reported as
`UNSUPPORTED` (the engine doesn't implement that operation), other `4xx` as
`WARNING`, and `5xx`/timeout as `FAIL`.

**Correctness:** CONF scenarios do not use golden result validators — they only
check HTTP class. Where `$evaluate` is called, CQL is the trivial
`ConformanceTrue` define so the probe stays wire-focused.

### System operations

| ID | Operation | Verb | Intended to test |
| --- | --- | --- | --- |
| CONF001 | `/metadata` | GET | Server publishes a CapabilityStatement (capability discovery). |
| CONF002 | `/$cql` | GET | Ad-hoc system-level CQL evaluation via GET. |
| CONF003 | `/$cql` | POST | Ad-hoc system-level CQL evaluation via POST. |

### `Library` operations

`$evaluate` runs a library's expressions; `$data-requirements` computes the data a
library needs.

| ID | Operation | Verb | Intended to test |
| --- | --- | --- | --- |
| CONF010 | `/Library/$evaluate` | GET | Type-level library evaluation via GET. |
| CONF011 | `/Library/$evaluate` | POST | Type-level library evaluation via POST. |
| CONF012 | `/Library/{id}/$evaluate` | POST | Instance-level library evaluation. |
| CONF013 | `/Library/$data-requirements` | GET | Type-level data-requirements via GET. |
| CONF014 | `/Library/$data-requirements` | POST | Type-level data-requirements via POST. |
| CONF015 | `/Library/{id}/$data-requirements` | GET | Instance-level data-requirements via GET. |
| CONF016 | `/Library/{id}/$data-requirements` | POST | Instance-level data-requirements via POST. |

### `Measure` operations

The measure family covers quality-measure evaluation and the reporting operations
around it.

| ID | Operation | Verb | Intended to test |
| --- | --- | --- | --- |
| CONF020 | `/Measure/$evaluate-measure` | GET | Type-level measure evaluation via GET. |
| CONF021 | `/Measure/$evaluate-measure` | POST | Type-level measure evaluation via POST. |
| CONF022 | `/Measure/{id}/$evaluate-measure` | GET | Instance-level measure evaluation via GET. |
| CONF023 | `/Measure/{id}/$evaluate-measure` | POST | Instance-level measure evaluation via POST. |
| CONF030 | `/Measure/$care-gaps` | POST | Type-level gaps-in-care reporting. |
| CONF031 | `/Measure/{id}/$care-gaps` | POST | Instance-level gaps-in-care reporting. |
| CONF032 | `/Measure/$collect-data` | POST | Type-level data collection for a measure. |
| CONF033 | `/Measure/{id}/$collect-data` | POST | Instance-level data collection. |
| CONF034 | `/Measure/$submit-data` | POST | Type-level submission of collected measure data. |
| CONF035 | `/Measure/{id}/$submit-data` | POST | Instance-level submission of collected data. |
| CONF036 | `/Measure/$data-requirements` | GET | Type-level measure data-requirements via GET. |
| CONF037 | `/Measure/$data-requirements` | POST | Type-level measure data-requirements via POST. |
| CONF038 | `/Measure/{id}/$data-requirements` | GET | Instance-level measure data-requirements via GET. |
| CONF039 | `/Measure/{id}/$data-requirements` | POST | Instance-level measure data-requirements via POST. |

### `PlanDefinition` operations

`$apply` is the clinical-decision-support entry point; `$package` bundles a
definition with its dependencies.

| ID | Operation | Verb | Intended to test |
| --- | --- | --- | --- |
| CONF040 | `/PlanDefinition/$apply` | GET | Type-level apply (CDS) via GET. |
| CONF041 | `/PlanDefinition/$apply` | POST | Type-level apply (CDS) via POST. |
| CONF042 | `/PlanDefinition/{id}/$apply` | GET | Instance-level apply via GET. |
| CONF043 | `/PlanDefinition/{id}/$apply` | POST | Instance-level apply via POST. |
| CONF044 | `/PlanDefinition/$package` | GET | Type-level packaging via GET. |
| CONF045 | `/PlanDefinition/$package` | POST | Type-level packaging via POST. |
| CONF046 | `/PlanDefinition/{id}/$package` | GET | Instance-level packaging via GET. |
| CONF047 | `/PlanDefinition/{id}/$package` | POST | Instance-level packaging via POST. |
| CONF048 | `/PlanDefinition/$data-requirements` | GET | Type-level data-requirements via GET. |
| CONF049 | `/PlanDefinition/$data-requirements` | POST | Type-level data-requirements via POST. |
| CONF050 | `/PlanDefinition/{id}/$data-requirements` | GET | Instance-level data-requirements via GET. |
| CONF051 | `/PlanDefinition/{id}/$data-requirements` | POST | Instance-level data-requirements via POST. |

### `ActivityDefinition` operations

| ID | Operation | Verb | Intended to test |
| --- | --- | --- | --- |
| CONF060 | `/ActivityDefinition/$apply` | GET | Type-level apply via GET. |
| CONF061 | `/ActivityDefinition/$apply` | POST | Type-level apply via POST. |
| CONF062 | `/ActivityDefinition/{id}/$apply` | GET | Instance-level apply via GET. |
| CONF063 | `/ActivityDefinition/{id}/$apply` | POST | Instance-level apply via POST. |

---

## Capability + performance scenarios (`CAP###`)

Each scenario below isolates one CQL construct. The point is not breadth of CQL
in a single query but a clean, comparable probe: change one thing, measure
correctness and cost. Each runs as `-P` (preload) and `-I` (inline).

Unless noted, the default mutator generates **40** `Condition` rows per patient
(**8** match / **32** nomatch at selectivity `0.2`), with **final** observations
on match rows and **cancelled** observations on nomatch rows.

### CAP001 — Count retrieve all of one resource

```cql
define "CountAllCondition":
  Count([Condition] C)
```

**Tests:** an unfiltered retrieve of every resource of a type, then an aggregate
`Count`. **Why it's hard / what it stresses:** this is the floor for retrieve
cost — the engine must materialize and model-map every `Condition`. Latency here
tracks raw retrieve-and-count throughput as data scales, with no filtering to
amortize. Use it as the baseline the filtered scenarios are compared against.

**Golden validation:** `tokenized_numeric_equals` with expression `total_count` →
**40** per patient (`valueInteger` on the count parameter).

### CAP002 — Retrieve based on valueset

```cql
define "CountValueSetRetrieve":
  Count([Condition: "Bench Condition ValueSet"] C)
```

**Tests:** a terminology-filtered retrieve, with valueset membership expressed
inside the retrieve (`[Condition: "…ValueSet"]`). **Why it's hard:** the engine
must resolve and expand the valueset and apply code membership during retrieval.
It probes terminology resolution and whether the engine can push the filter into
the retrieve rather than fetching everything first.

**Golden validation:** `round(total_count * selectivity)` → **8** per patient
(same expected count as CAP003).

### CAP003 — Valueset retrieve plus valueset predicate

```cql
define "CountValueSetWhere":
  Count([Condition] R where R.code in "Bench Condition ValueSet")
```

**Tests:** the *same logical result* as CAP002, but written as a post-retrieve
`where … in "ValueSet"` predicate instead of a typed retrieve. **Why it's hard:**
it reveals optimization differences — a naive engine retrieves all conditions and
filters in memory, while an optimizing engine recognizes the predicate is
equivalent to a filtered retrieve. **Comparing CAP002 vs. CAP003** on the same
engine is the interesting signal.

**Golden validation:** same as CAP002 — **8** via `round(total_count * selectivity)`.
Comparing CAP002 vs. CAP003 latency on the same engine is only meaningful when
both pass this check.

### CAP004 — Resource return projection

```cql
define "ReturnConditionIds":
  [Condition] R return R.id.value
```

**Tests:** a `return` projection that materializes a value per resource rather
than aggregating. **Why it's hard:** unlike the `Count` scenarios, the engine must
build and serialize a full result list. It stresses result-set materialization
and response serialization, and shows how response size affects latency.

**Golden validation:** `min_items` on the `ReturnConditionIds` parameter's `part`
array — at least **40** elements (one id per condition, unfiltered retrieve).

### CAP005 — Tuple populated from another define

```cql
define "BaseConditions":
  [Condition] C where C.code in "Bench Condition ValueSet"

define "TupleFromBase":
  Count(
    "BaseConditions" C
      return { id: Coalesce(C.id, ''), code: Coalesce(C.code.coding[0].code, '') }
  )
```

**Tests:** one define consuming another define's result, plus tuple construction
with `Coalesce` and nested path navigation (`code.coding[0].code`). **Why it's
hard:** it exercises the define dependency graph (does the engine evaluate and
reuse `BaseConditions` cleanly?) together with structured-value construction and
null-safe accessors.

**Golden validation:** `round(total_count * selectivity)` → **8** (only
valueset-matching conditions from `BaseConditions`).

### CAP006 — Retrieve with `with`-clause join

```cql
define "CountWithJoin":
  Count(
    [Condition] C
      with [Observation] O
        such that O.subject.reference.value = 'Patient/' + Patient.id.value
          and O.code ~ C.code
  )
```

**Tests:** a correlated semi-join between `Condition` and `Observation` on subject
and code equivalence (`~`). **Why it's hard:** without optimization the cost is
roughly |Condition| × |Observation| per patient. It probes join evaluation
strategy and code-equivalence semantics, and is where engines with naive nested
iteration show their cost most clearly.

**Fixture design:** scenario-local `mutator.yaml` links **only** `ConditionMatch`
to `ObservationFinal`. Nomatch conditions have **no** related observation, so the
semi-join cannot spuriously match via a cancelled obs on a nomatch code.

**Golden validation:** `round(total_count * selectivity)` → **8** (only the eight
match rows satisfy `with [Observation] … and O.code ~ C.code`).

### CAP007 — Retrieve with `without`-clause join

```cql
define "CountWithoutJoin":
  Count(
    [Condition] C
      without [Observation] O
        such that O.subject.reference.value = 'Patient/' + Patient.id.value
          and O.status.value = 'cancelled'
          and O.code ~ C.code
  )
```

**Tests:** an anti-join — conditions with **no** matching cancelled observation.
**Why it's hard:** negation is harder to optimize than the semi-join in CAP006;
the engine must prove absence across the correlated set rather than stop at the
first match. Comparing CAP006 vs. CAP007 isolates semi-join vs. anti-join cost.

**Fixture design:** default mutator — nomatch rows include a **cancelled**
observation correlated on code, so they are excluded by `without … status =
'cancelled'`.

**Golden validation:** `round(total_count * selectivity)` → **8** (conditions with
no matching cancelled observation).

### CAP008 — Query with sort

```cql
define "SortedConditionIds":
  [Condition] C
    sort by id.value
```

**Tests:** a retrieve followed by `sort by` on a discriminating key (`id.value`),
not a field that is identical on every row. **Why it's hard:** it exercises the
engine's sort path and stable-ordering behavior over a result list — separate
machinery from filtering and aggregation, and a common source of cost on large
result sets.

**Golden validation:**

- `min_items` on `SortedConditionIds` `part` — **40** ids.
- `response_regex` on the raw body — match ids (`…-m-…`) appear before nomatch ids
  (`…-n-…`) in serialized output, proving sort order is not arbitrary.

### CAP009 — Complex predicate with function calls

```cql
define function "ComplexMatch"(C Condition):
  C.recordedDate is not null
    and StartsWith(ToString(C.recordedDate), '2024')
    and exists(C.clinicalStatus.coding CS where CS.code = 'active')
    and Length(Coalesce(C.id, '')) > 5
    and C.code in "Bench Condition ValueSet"

define "ComplexPredicateCount":
  Count([Condition] C where "ComplexMatch"(C))
```

**Tests:** a user-defined function invoked per row inside a `where`, combining
null checks, string/temporal handling (`ToString`, `StartsWith`), a nested
`exists`, `Length`/`Coalesce`, and valueset membership. **Why it's hard:** it
stresses per-row function-call overhead and breadth of the engine's function
library all at once — the most computationally demanding predicate in the suite.

**Golden validation:** `round(total_count * selectivity)` → **8** at default
selectivity `0.2`.

### CAP010 — Many returned results with `exists`

```cql
define "ExistsManyResults":
  exists([Condition] C where C.code in "Bench Condition ValueSet")
```

**Tests:** existence over a large filtered set. **Why it's hard:** the correct,
efficient behavior is to short-circuit at the first match; a naive engine
materializes the whole filtered set before answering. With many matches present,
this scenario distinguishes engines that short-circuit `exists` from those that
don't.

**Selectivity:** `selectivity: 0.5` on `scenario.yaml` (overrides the suite
default `0.2`) so **half** of generated conditions match the valueset — a denser
positive set for `exists` without changing the CQL.

**Golden validation:** `value_type_and_equals` — `valueBoolean: true` on the
`exists` result (any matching parameter node).

### CAP011 — `let` expression

```cql
define "LetCount":
  Count(
    [Condition] C
      let CId: C.id
      where CId is not null
  )
```

**Tests:** a `let` binding scoped inside a query, followed by a null filter and
count. **Why it's hard:** it exercises query-scoped variable binding and
evaluation order — a correctness probe for `let` handling more than a heavy
performance load.

**Fixture design:** `fixed_templates` adds **two** extra `ConditionMissingId`
instances (no `id` field) on top of the usual 40 generated conditions.

**Golden validation:** `tokenized_numeric_equals` with expression
`total_count - null_id_count` → **38** per patient (`null_id_count` is **2** from
the harness context).

---

## Coverage at a glance

| Construct | Scenario | Compare against |
| --- | --- | --- |
| Unfiltered retrieve + count | CAP001 | Baseline for all others |
| Valueset retrieve | CAP002 | CAP003 (predicate form) |
| Valueset predicate | CAP003 | CAP002 (retrieve form) |
| Return projection | CAP004 | CAP001 (count vs. materialize) |
| Define-to-define + tuples | CAP005 | — |
| Semi-join (`with`) | CAP006 | CAP007 (anti-join) |
| Anti-join (`without`) | CAP007 | CAP006 (semi-join) |
| Sort | CAP008 | — |
| Complex predicate + functions | CAP009 | — |
| `exists` short-circuit | CAP010 | CAP002 (count vs. exists) |
| `let` binding | CAP011 | — |

Each row runs as both preload (`-P`) and inline (`-I`); compare the two variants
to see how an engine's resident-data path compares to its inline-data path.
