---
title: Overview
description: What CQF Bench is, who it's for, and how the harness is structured.
---

CQF Bench is an open benchmark harness for comparing the behavior and performance
of servers that implement the FHIR Clinical Reasoning module and the Clinical
Quality Framework (CQF) operation families. It runs a versioned catalog of
scenarios against one or more engines, normalizes each engine's API differences
through adapters, validates correctness beyond the HTTP status code, and writes
reproducible reports.

## Who it's for

- **Healthcare interoperability engineers** evaluating or operating CQF servers.
- **Clinical quality developers** who need to know which CQL constructs an engine
  evaluates correctly and how cost scales with data volume.
- **CQL / CQF implementers** who want a fixed, external conformance and
  performance target while developing an engine.
- **Open-source contributors** extending the scenario catalog or onboarding new
  engines.

## What problem it solves

CQF and CQL implementations diverge in ways that are hard to compare informally:

- **Operation coverage** — which `Library`, `Measure`, `PlanDefinition`, and
  `ActivityDefinition` operations are implemented, and over which verbs.
- **API shape** — how libraries and data are submitted (resident vs. inline,
  `Parameters` vs. `Bundle`, instance vs. type-level operations).
- **Correctness** — whether a given CQL pattern returns the right answer.
- **Performance** — how latency behaves as data scales.

CQF Bench turns those questions into a repeatable measurement. The same suite,
the same deterministically generated data, and the same scoring rules run against
every engine, so results can be diffed, published, and trusted.

## How it's structured

A run moves through three phases that you can invoke together or separately:

1. **Generate** — Produce deterministic FHIR payloads for each scenario from FSH
   templates and a selectivity-driven mutator.
2. **Load** — Preload required libraries, measures, valuesets, and setup data into
   the target engine.
3. **Execute** — Run each scenario's request, classify the HTTP outcome, validate
   correctness, and record timing for correct responses only.

The harness is intentionally dependency-light: a set of Python scripts under
`scripts/`, YAML configuration under `bench/`, and PyYAML as the only runtime
dependency. Engines run as Docker containers (or any reachable endpoint you
configure).

## Core building blocks

| Concept | What it is |
| --- | --- |
| **Engine** | A target server under test, described in an engines config file. |
| **Adapter** | Per-engine logic that rewrites paths, methods, and payloads. |
| **Suite** | An ordered list of scenarios with shared defaults and HTTP policy. |
| **Scenario (test case)** | A single check: an operation, its CQL, expected HTTP, and validators. |
| **Selectivity** | The fraction of generated data expected to match a scenario's logic. |
| **Result** | The per-scenario, per-engine outcome plus timing, written to JSON and Markdown. |

See [Core Concepts](/cqf-bench/concepts/) for the full model.

## Two classes of test

CQF Bench distinguishes **conformance** from **capability + performance**:

- **Conformance (`CONF###`)** — Is the endpoint and verb reachable, and does it
  return a CQF-conformant status code? Untimed, red/green by HTTP class.
- **Capability + Performance (`CAP###-P` / `CAP###-I`)** — Does data-backed CQL
  produce the correct result, and how fast? Timed **only** on correct responses.

This separation keeps performance numbers honest: a server is never credited with
fast timing for a response that was wrong or unsupported.

## What it is not

- It is **not** a CQL engine or a FHIR server. It exercises engines you provide.
- It is **not** a conformance certification. It is a transparent, reproducible
  measurement you can inspect and extend.
- It does **not** ship patient data. All fixtures are synthetic and generated.

## Next steps

- [Getting Started](/cqf-bench/getting-started/) — a minimal end-to-end run.
- [Installation](/cqf-bench/installation/) — prerequisites and setup.
- [Core Concepts](/cqf-bench/concepts/) — the full model behind the harness.
