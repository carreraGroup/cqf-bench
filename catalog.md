# CQF Bench Scenario Catalog

This catalog is the editable source of truth for scenario intent and audit status.

## How to use this file

- Update `Intent` as tests evolve.
- During audits, set `Audit Status`, `Last Audit`, and `Notes`.
- Keep IDs aligned with `bench/scenarios/tpcqf/suite.yaml`.

Audit status vocabulary: `Not Audited`, `Pass`, `Needs Work`, `Deprecated`.

## Type 1: Conformance Tests (CONF###)

Purpose: strict endpoint/verb conformance checks for CQF IG operation families. Untimed red/green checks based on expected HTTP outcomes.

**Scope (wire only):** CONF scenarios use trivial CQL (`ConformanceTrue`) and do **not** validate evaluation results. Audit status here means route/verb HTTP policy review, not clinical correctness. See `docs/TPCQF_GOLDEN_VALIDATION.md`.

| ID | Name | Endpoint | Verb | Intent | Audit Status | Last Audit | Notes |
|---|---|---|---|---|---|---|---|
| CONF001 | GET /metadata conformance | `/metadata` | `GET` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF002 | GET /$cql conformance | `/$cql` | `GET` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF003 | POST /$cql conformance | `/$cql` | `POST` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF010 | GET /Library/$evaluate conformance | `/Library/$evaluate` | `GET` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF011 | POST /Library/$evaluate conformance | `/Library/$evaluate` | `POST` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF012 | POST /Library/{id}/$evaluate conformance | `/Library/BenchCONF012/$evaluate` | `POST` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF013 | GET /Library/$data-requirements conformance | `/Library/$data-requirements` | `GET` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF014 | POST /Library/$data-requirements conformance | `/Library/$data-requirements` | `POST` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF015 | GET /Library/{id}/$data-requirements conformance | `/Library/BenchCONF015/$data-requirements` | `GET` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF016 | POST /Library/{id}/$data-requirements conformance | `/Library/BenchCONF016/$data-requirements` | `POST` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF020 | GET /Measure/$evaluate-measure conformance | `/Measure/$evaluate-measure` | `GET` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF021 | POST /Measure/$evaluate-measure conformance | `/Measure/$evaluate-measure` | `POST` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF022 | GET /Measure/{id}/$evaluate-measure conformance | `/Measure/Test/$evaluate-measure` | `GET` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF023 | POST /Measure/{id}/$evaluate-measure conformance | `/Measure/Test/$evaluate-measure` | `POST` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF030 | POST /Measure/$care-gaps conformance | `/Measure/$care-gaps` | `POST` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF031 | POST /Measure/{id}/$care-gaps conformance | `/Measure/Test/$care-gaps` | `POST` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF032 | POST /Measure/$collect-data conformance | `/Measure/$collect-data` | `POST` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF033 | POST /Measure/{id}/$collect-data conformance | `/Measure/Test/$collect-data` | `POST` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF034 | POST /Measure/$submit-data conformance | `/Measure/$submit-data` | `POST` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF035 | POST /Measure/{id}/$submit-data conformance | `/Measure/Test/$submit-data` | `POST` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF036 | GET /Measure/$data-requirements conformance | `/Measure/$data-requirements` | `GET` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF037 | POST /Measure/$data-requirements conformance | `/Measure/$data-requirements` | `POST` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF038 | GET /Measure/{id}/$data-requirements conformance | `/Measure/Test/$data-requirements` | `GET` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF039 | POST /Measure/{id}/$data-requirements conformance | `/Measure/Test/$data-requirements` | `POST` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF040 | GET /PlanDefinition/$apply conformance | `/PlanDefinition/$apply` | `GET` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF041 | POST /PlanDefinition/$apply conformance | `/PlanDefinition/$apply` | `POST` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF042 | GET /PlanDefinition/{id}/$apply conformance | `/PlanDefinition/Test/$apply` | `GET` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF043 | POST /PlanDefinition/{id}/$apply conformance | `/PlanDefinition/Test/$apply` | `POST` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF044 | GET /PlanDefinition/$package conformance | `/PlanDefinition/$package` | `GET` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF045 | POST /PlanDefinition/$package conformance | `/PlanDefinition/$package` | `POST` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF046 | GET /PlanDefinition/{id}/$package conformance | `/PlanDefinition/Test/$package` | `GET` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF047 | POST /PlanDefinition/{id}/$package conformance | `/PlanDefinition/Test/$package` | `POST` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF048 | GET /PlanDefinition/$data-requirements conformance | `/PlanDefinition/$data-requirements` | `GET` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF049 | POST /PlanDefinition/$data-requirements conformance | `/PlanDefinition/$data-requirements` | `POST` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF050 | GET /PlanDefinition/{id}/$data-requirements conformance | `/PlanDefinition/Test/$data-requirements` | `GET` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF051 | POST /PlanDefinition/{id}/$data-requirements conformance | `/PlanDefinition/Test/$data-requirements` | `POST` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF060 | GET /ActivityDefinition/$apply conformance | `/ActivityDefinition/$apply` | `GET` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF061 | POST /ActivityDefinition/$apply conformance | `/ActivityDefinition/$apply` | `POST` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF062 | GET /ActivityDefinition/{id}/$apply conformance | `/ActivityDefinition/Test/$apply` | `GET` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |
| CONF063 | POST /ActivityDefinition/{id}/$apply conformance | `/ActivityDefinition/Test/$apply` | `POST` | Verify endpoint/verb is reachable and returns a CQF-conformant status code. | Audited | 2026-03-11 |  |

## Type 2: Capability + Performance Tests (CAP###-P/I)

Purpose: data-backed CQL capability and performance checks. Timed only on PASS (expected HTTP + correctness).

**Golden validation:** Each CAP scenario asserts expected results via `expected.yaml` (see `docs/TPCQF_GOLDEN_VALIDATION.md`). Per-patient formulas use `total_count`, `selectivity`, and scenario-specific mutator overlays (CAP006 semi-join, CAP011 null ids).

| ID | Variant | Name | Intent | Timed? | Scenario Dir | Audit Status | Last Audit | Notes |
|---|---|---|---|---|---|---|---|---|
| CAP001-P | Preload | Count retrieve all of one resource (preload) | Exercise specific CQL behavior with preloaded resident data + restart mode. | PASS only | `bench/scenarios/tpcqf/CAP001-P/` | Audited | 2026-03-11 | Golden: `total_count` (40) |
| CAP001-I | Inline | Count retrieve all of one resource (inline) | Exercise specific CQL behavior with inline data bundle mode. | PASS only | `bench/scenarios/tpcqf/CAP001-I/` | Audited | 2026-03-11 | Golden: `total_count` (40) |
| CAP002-P | Preload | Retrieve based on valueset (preload) | Exercise specific CQL behavior with preloaded resident data + restart mode. | PASS only | `bench/scenarios/tpcqf/CAP002-P/` | Audited | 2026-03-11 | Golden: `round(total_count*selectivity)`; pair with CAP003 |
| CAP002-I | Inline | Retrieve based on valueset (inline) | Exercise specific CQL behavior with inline data bundle mode. | PASS only | `bench/scenarios/tpcqf/CAP002-I/` | Audited | 2026-03-11 | Golden: `round(total_count*selectivity)`; pair with CAP003 |
| CAP003-P | Preload | Valueset retrieve plus valueset predicate (preload) | Exercise specific CQL behavior with preloaded resident data + restart mode. | PASS only | `bench/scenarios/tpcqf/CAP003-P/` | Audited | 2026-03-11 | Golden: same as CAP002 (equivalence) |
| CAP003-I | Inline | Valueset retrieve plus valueset predicate (inline) | Exercise specific CQL behavior with inline data bundle mode. | PASS only | `bench/scenarios/tpcqf/CAP003-I/` | Audited | 2026-03-11 | Golden: same as CAP002 (equivalence) |
| CAP004-P | Preload | Resource return projection (preload) | Exercise specific CQL behavior with preloaded resident data + restart mode. | PASS only | `bench/scenarios/tpcqf/CAP004-P/` | Audited | 2026-03-11 | Golden: list `part` min 40 |
| CAP004-I | Inline | Resource return projection (inline) | Exercise specific CQL behavior with inline data bundle mode. | PASS only | `bench/scenarios/tpcqf/CAP004-I/` | Audited | 2026-03-11 | Golden: list `part` min 40 |
| CAP005-P | Preload | Tuple populated from another define (preload) | Exercise specific CQL behavior with preloaded resident data + restart mode. | PASS only | `bench/scenarios/tpcqf/CAP005-P/` | Audited | 2026-03-11 | Golden: `round(total_count*selectivity)` |
| CAP005-I | Inline | Tuple populated from another define (inline) | Exercise specific CQL behavior with inline data bundle mode. | PASS only | `bench/scenarios/tpcqf/CAP005-I/` | Audited | 2026-03-11 | Golden: `round(total_count*selectivity)` |
| CAP006-P | Preload | Retrieve with with-clause join (preload) | Exercise specific CQL behavior with preloaded resident data + restart mode. | PASS only | `bench/scenarios/tpcqf/CAP006-P/` | Audited | 2026-03-11 | Golden: 8; local mutator (no nomatch linked obs) |
| CAP006-I | Inline | Retrieve with with-clause join (inline) | Exercise specific CQL behavior with inline data bundle mode. | PASS only | `bench/scenarios/tpcqf/CAP006-I/` | Audited | 2026-03-11 | Golden: 8; local mutator |
| CAP007-P | Preload | Retrieve with without-clause join (preload) | Exercise specific CQL behavior with preloaded resident data + restart mode. | PASS only | `bench/scenarios/tpcqf/CAP007-P/` | Audited | 2026-03-11 | Golden: `round(total_count*selectivity)` |
| CAP007-I | Inline | Retrieve with without-clause join (inline) | Exercise specific CQL behavior with inline data bundle mode. | PASS only | `bench/scenarios/tpcqf/CAP007-I/` | Audited | 2026-03-11 | Golden: `round(total_count*selectivity)` |
| CAP008-P | Preload | Query with sort (preload) | Exercise specific CQL behavior with preloaded resident data + restart mode. | PASS only | `bench/scenarios/tpcqf/CAP008-P/` | Audited | 2026-03-11 | Golden: 40 parts; sort by id; regex order |
| CAP008-I | Inline | Query with sort (inline) | Exercise specific CQL behavior with inline data bundle mode. | PASS only | `bench/scenarios/tpcqf/CAP008-I/` | Audited | 2026-03-11 | Golden: 40 parts; sort by id; regex order |
| CAP009-P | Preload | Complex predicate with function calls (preload) | Exercise specific CQL behavior with preloaded resident data + restart mode. | PASS only | `bench/scenarios/tpcqf/CAP009-P/` | Audited | 2026-03-11 | Golden: `round(total_count*selectivity)` |
| CAP009-I | Inline | Complex predicate with function calls (inline) | Exercise specific CQL behavior with inline data bundle mode. | PASS only | `bench/scenarios/tpcqf/CAP009-I/` | Audited | 2026-03-11 | Golden: `round(total_count*selectivity)` |
| CAP010-P | Preload | Many returned results with exists (preload) | Exercise specific CQL behavior with preloaded resident data + restart mode. | PASS only | `bench/scenarios/tpcqf/CAP010-P/` | Audited | 2026-03-11 | Golden: `valueBoolean` true; selectivity 0.5 |
| CAP010-I | Inline | Many returned results with exists (inline) | Exercise specific CQL behavior with inline data bundle mode. | PASS only | `bench/scenarios/tpcqf/CAP010-I/` | Audited | 2026-03-11 | Golden: `valueBoolean` true; selectivity 0.5 |
| CAP011-P | Preload | Let expression (preload) | Exercise specific CQL behavior with preloaded resident data + restart mode. | PASS only | `bench/scenarios/tpcqf/CAP011-P/` | Audited | 2026-03-11 | Golden: `total_count - null_id_count` (38) |
| CAP011-I | Inline | Let expression (inline) | Exercise specific CQL behavior with inline data bundle mode. | PASS only | `bench/scenarios/tpcqf/CAP011-I/` | Audited | 2026-03-11 | Golden: `total_count - null_id_count` (38) |

## Optional Audit Checklist (per scenario)

- `scenario.cql` matches stated intent and expected behavior.
- `expected.yaml` validates correctness beyond HTTP status where applicable.
- For `-P` scenarios, preload/restart flow is configured and verified.
- For `-I` scenarios, inline payload generation is configured and verified.
- FAIL results are excluded from timing; PASS results include timing.
