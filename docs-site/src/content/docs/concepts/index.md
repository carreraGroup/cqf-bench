---
title: Core Concepts
description: The model behind CQF Bench — engines, adapters, suites, scenarios, selectivity, scoring, and results.
slug: concepts
---

This page describes the model CQF Bench is built on. The detail pages —
[Benchmark Suites](/cqf-bench/concepts/benchmark-suites/),
[Test Cases](/cqf-bench/concepts/test-cases/),
[Engine Adapters](/cqf-bench/concepts/engine-adapters/), and
[Results](/cqf-bench/concepts/results/) — expand each piece.

## The big picture

A benchmark run takes a **suite** of **scenarios**, generates deterministic data,
runs each scenario against one or more **engines** through **adapters**, scores
the outcome, and writes **results**.

```
suite.yaml ──▶ scenarios ──▶ [ generate → load → execute ] ──▶ results (.json + .md)
                  │                         ▲
                  └── adapters per engine ──┘
```

## Engine

An **engine** is a target server under test — anything that exposes CQF /
Clinical Reasoning REST operations. Engines are declared in an engines config
file (for local runs, `bench/config/local.engines.yaml`). Each engine entry
carries:

- a `name` and an `adapter` (which adapter class to use),
- a `base_url` plus base paths (`cqf_base_path`, `fhir_base_path`,
  `data_base_path`),
- optional `headers` (with `${VAR}` expansion for secrets),
- a list of `capabilities` it supports,
- optional `docker` settings for local container management,
- optional `disabled` / `disabled_reason` flags.

Candidate engines include Mercury, HAPI CQF Ruler, Firely-based runtimes, Smile
CDR, LinuxForHealth FHIR, and Blaze FHIR.

## Capability

A **capability** is a tag describing what an engine can do, for example:

- `resident_data_load` — accepts data preloaded into the server,
- `resident_execute` — evaluates against resident (preloaded) data,
- `inline_bundle_execute` — accepts data inline in the request payload,
- `system_cql` — supports system-level `$cql`,
- `library_write_once_execute_many` — supports persisting a library and
  re-evaluating it.

A scenario declares the capabilities it requires. If an engine lacks them, the
scenario is **skipped** for that engine rather than failed. See
[Engine Adapters](/cqf-bench/concepts/engine-adapters/).

## Adapter

Engines differ in how they accept the same logical request. An **adapter**
encapsulates those differences — rewriting the path, HTTP method, query
parameters, and payload — so a single scenario definition runs unchanged across
engines. Adapters are selected per engine via the `adapter` field. See
[Engine Adapters](/cqf-bench/concepts/engine-adapters/).

## Suite

A **suite** is an ordered collection of scenarios with shared defaults
(`timeout_seconds`, `concurrency`, `selectivity`, …) and a default HTTP outcome
policy. The reference suite is `TPCQF`, defined in
`bench/scenarios/tpcqf/suite.yaml`, which lists its scenarios by ID under
`scenario_ids`. See [Benchmark Suites](/cqf-bench/concepts/benchmark-suites/).

## Scenario (test case)

A **scenario** is one check. It lives in its own folder and describes the
operation under test, its CQL, the expected HTTP outcome, correctness validators,
and — for data-backed tests — how to generate its data. Scenarios come in two
classes:

- **Conformance (`CONF###`)** — endpoint/verb reachability and CQF-conformant
  status codes. Untimed.
- **Capability + Performance (`CAP###-P` / `CAP###-I`)** — data-backed CQL
  correctness and latency. Timed only on correct responses.

See [Test Cases](/cqf-bench/concepts/test-cases/).

## Selectivity

**Selectivity** is the fraction of generated data expected to match a scenario's
logic — e.g. a selectivity of `0.2` means roughly 20% of generated conditions
match the scenario's valueset or predicate. It is applied deterministically by
the data generator so that result counts are predictable and correctness can be
asserted. The default is `0.2`, overridable per suite or per scenario.

## Scoring

Scoring is deliberately strict and separates HTTP outcome from correctness:

- **Conformance** scenarios are scored by HTTP class against the scenario's
  `expected_http` policy: `PASS` (2xx), `UNSUPPORTED` (e.g. 422), `WARNING`
  (other 4xx needing attention), `FAIL` (5xx / timeout).
- **Capability** scenarios `PASS` only when the HTTP outcome is success **and**
  every correctness validator passes. Anything else is `FAIL`.
- **Timing is recorded only for PASS responses.** Failed, unsupported, and
  timed-out requests are excluded from latency percentiles, so an engine is never
  credited with fast timing for a wrong or unsupported answer.

The `--score-mode` flag switches between `compat` (use each scenario's
`expected_http`) and `strict-2xx` (require 2xx for both setup and main calls).

## Results

Every run writes a JSON report and a Markdown summary, keyed by a `run_id`, a
hash of the suite files, and the git commit. The Markdown summary presents a
**Conformance Matrix** and a **Capability + Performance Matrix** with one column
group per engine. See [Results](/cqf-bench/concepts/results/) and the
[Output Format reference](/cqf-bench/reference/output-format/).

## The three phases

| Phase | Script | What it does |
| --- | --- | --- |
| **Generate** | `generate_scenario_data.py` | Produces deterministic payloads from FSH templates + mutator. |
| **Load** | `load_test_data.py` (or `run_benchmark.py --run-phase load`) | Preloads libraries, measures, valuesets, and setup data. |
| **Execute** | `execute_tests.py` (or `run_benchmark.py --run-phase execute`) | Runs scenarios, scores outcomes, records timing. |

`run_benchmark.py --run-phase full` does load + execute in one invocation.
