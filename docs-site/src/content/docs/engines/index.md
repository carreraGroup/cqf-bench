---
title: Engine guides
description: Configure CQF Bench to benchmark your engine — bring your own endpoint or follow a product-specific guide.
slug: engines
---

CQF Bench compares **engines**: FHIR servers (or gateways) that expose Clinical
Reasoning / CQF operations. Each engine is an entry in your engines config file,
optionally backed by a **product-specific guide** below.

## How engines fit in a run

1. You declare engines in `bench/config/local.engines.yaml` (from
   `engines.example.yaml`).
2. Each engine names an **adapter** that translates engine-neutral scenarios into
   that server's HTTP shape.
3. Scenarios declare **required capabilities**; engines missing a capability skip
   those scenarios (they are not failed).
4. You run the suite with `--filter-engine` or against all enabled engines. See
   [Compare Engines](/cqf-bench/guides/compare-engines/).

For the full adapter model, see [Engine Adapters](/cqf-bench/concepts/engine-adapters/).

## Product guides

Step-by-step setup for engines we document explicitly:

| Engine | Guide | Adapter | Notes |
| --- | --- | --- | --- |
| **HAPI CQF Ruler** | [HAPI CQF Ruler](/cqf-bench/engines/hapi-cqf-ruler/) | `hapi-cqf-ruler` | Open-source Docker image; recommended for first runs and release benchmarks. |
| **Mercury** | _Coming soon_ | `mercury-cqf` | Entry exists in `engines.example.yaml`; requires a locally built image. Dedicated doc page planned. |
| Blaze, Firely, Smile CDR, others | [Add an engine](/cqf-bench/guides/add-an-engine/) | `generic-cqf` or product adapter | Template entries in `engines.example.yaml`; configure your endpoint and capabilities. |

## Bring your own engine

Any CQF-capable endpoint can be benchmarked if you:

1. Add a YAML block with the correct `base_url`, paths, and **capabilities**.
2. Pick an adapter (`generic-cqf` when the server already matches scenario
   shapes, or implement a new adapter when it does not).

Walkthrough: **[Add an engine](/cqf-bench/guides/add-an-engine/)**.

## Quick reference

```bash
# Copy template config
cp bench/config/engines.example.yaml bench/config/local.engines.yaml

# Bootstrap a documented engine (example: HAPI CQF Ruler)
python scripts/manage_engines.py bootstrap \
  --engines bench/config/local.engines.yaml \
  --engine hapi-cqf-ruler-local

# Run against one engine
python scripts/run_benchmark.py \
  --engines bench/config/local.engines.yaml \
  --suite bench/scenarios/tpcqf/suite.yaml \
  --scale 100 \
  --filter-engine hapi-cqf-ruler-local
```

Field-level schema: [Configuration Reference](/cqf-bench/reference/configuration/).
