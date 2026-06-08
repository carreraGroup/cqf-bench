---
title: Mercury
description: Run CQF Bench against Mercury with the mercury-cqf adapter, including preload and inline capability scenarios.
---

**Mercury** is supported in CQF Bench through the `mercury-cqf` adapter and a
template engine entry in `bench/config/engines.example.yaml`.

Use this guide for local Mercury runs and side-by-side comparison against HAPI
or other engines.

## Template entry

In `bench/config/engines.example.yaml` the engine is named
**`mercury-local`**.

| Setting | Value |
| --- | --- |
| `adapter` | `mercury-cqf` |
| `base_url` | `http://localhost:8080` |
| `cqf_base_path` | `/cqf` |
| `fhir_base_path` | `/fhir` |
| `data_base_path` | `/api` |
| Docker image | `mercury-cqf-bench:latest` |
| Host port | `8080` → container `8080` |
| Suggested local fairness caps | `cpus: 4.0`, `mem_limit: 8g`, `cpuset: "0-3"` |
| Health check | `GET http://localhost:8080/cqf/metadata` |

Copy the template:

```bash
cp bench/config/engines.example.yaml bench/config/local.engines.yaml
```

## Start the server

From repo root:

```bash
python scripts/manage_engines.py bootstrap \
  --engines bench/config/local.engines.yaml \
  --engine mercury-local
```

Verify:

```bash
python scripts/manage_engines.py health \
  --engines bench/config/local.engines.yaml \
  --engine mercury-local
```

Expect HTTP `200` from `http://localhost:8080/cqf/metadata`.

## Declared capabilities

Template capabilities:

- `resident_data_load`
- `resident_execute`
- `system_cql`
- `inline_bundle_execute`

That covers both preload (`CAP###-P`) and inline (`CAP###-I`) capability
scenarios.

## What the `mercury-cqf` adapter does

- Rewrites setup data loads to Mercury’s data endpoint shape.
- Routes `Library/$evaluate` calls to instance form (`/Library/{id}/$evaluate`)
  when library ids are known.
- Normalizes payload details for Mercury’s canonical/library parameter handling.

Scenario files stay engine-neutral; engine-specific request shaping is done in
the adapter.

## Run the benchmark

```bash
python scripts/run_benchmark.py \
  --run-phase execute \
  --engines bench/config/local.engines.yaml \
  --suite bench/scenarios/tpcqf/suite.yaml \
  --scale 100 \
  --filter-engine mercury-local
```

Reports are written as JSON and Markdown run artifacts.

## Observed behavior (May 28, 2026)

These notes are engine-specific observations from local benchmark runs.

- Mercury executed full `TPCQF` runs with stable transport in the tested setup.
- In full capability validation at scale 100, Mercury passed CAP scenarios that
  match currently supported operations, including CAP002/CAP003 parity and
  correctness checks for CAP004, CAP006, CAP008, and CAP011.
- Preload-library and preload-data paths behaved consistently after lifecycle
  cleanup fixes in the harness.

For reproducible comparisons, record:

1. exact phases (`generate` / `load` / `execute`) and whether payloads came from `--generated-data-root`,
2. scale/concurrency/timeout,
3. image tag and digest (or local build commit),
4. report JSON artifacts.

## Related

- [Engine guides](/cqf-bench/engines/)
- [Engine Adapters](/cqf-bench/concepts/engine-adapters/)
- [Compare Engines](/cqf-bench/guides/compare-engines/)
