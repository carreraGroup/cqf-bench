---
title: Compare Engines
description: Run the same suite against multiple engines and read the side-by-side matrices.
---

The point of CQF Bench is comparison: run the same scenarios, the same data, and
the same scoring rules across multiple engines, then read the results side by
side. This guide shows how.

New to engine setup? Start with [Engine guides](/cqf-bench/engines/) or
[Add an engine](/cqf-bench/guides/add-an-engine/). For HAPI CQF Ruler specifically,
see [HAPI CQF Ruler](/cqf-bench/engines/hapi-cqf-ruler/).

## 1. Configure multiple engines

Your engines config (`bench/config/local.engines.yaml`) can declare any number of
engines. Each names its adapter, base URL, base paths, capabilities, and (for
local containers) Docker settings. The shipped template (`engines.example.yaml`)
includes **HAPI CQF Ruler** and **Mercury**; enable Mercury only after you have a
local benchmark image.

```yaml
engines:
  - name: hapi-cqf-ruler-local
    adapter: hapi-cqf-ruler
    base_url: http://localhost:8081
    cqf_base_path: /fhir
    fhir_base_path: /fhir
    data_base_path: /fhir
    capabilities: [resident_data_load, resident_execute, system_cql, inline_bundle_execute]
    docker:
      enabled: true
      image: alphora/cqf-ruler:latest
      container_name: hapi-cqf-ruler
      host_port: 8081
      container_port: 8080
      health_path: /fhir/metadata

  # mercury-local ships disabled in the template; set disabled: false after
  # building mercury-cqf-bench:latest (see Engine guides → Mercury).
  - name: mercury-local
    adapter: mercury-cqf
    base_url: http://localhost:8080
    cqf_base_path: /cqf
    fhir_base_path: /fhir
    data_base_path: /api
    disabled: true
    capabilities: [resident_data_load, resident_execute, system_cql, inline_bundle_execute, library_write_once_execute_many]
    docker:
      enabled: true
      image: mercury-cqf-bench:latest
      container_name: mercury-cqf-bench
      host_port: 8080
      container_port: 8080
      health_path: /cqf/metadata
```

See the [Configuration Reference](/cqf-bench/reference/configuration/) for every
field, and [Engine Adapters](/cqf-bench/concepts/engine-adapters/) for adapter
selection.

## 2. Bring the engines up

```bash
python scripts/manage_engines.py bootstrap \
  --engines bench/config/local.engines.yaml \
  --engine hapi-cqf-ruler-local

# Optional second engine — enable mercury-local in YAML first, then:
# python scripts/manage_engines.py bootstrap \
#   --engines bench/config/local.engines.yaml \
#   --engine mercury-local

python scripts/manage_engines.py health \
  --engines bench/config/local.engines.yaml
```

Omitting `--engine` applies the action to every Docker-enabled engine that is not
marked `disabled: true`.

## 3. Use identical, fair inputs

For a fair comparison, every engine must see the same data. Generate once, then
load and execute against each engine from that same generated root:

```bash
python scripts/generate_scenario_data.py \
  --suite bench/scenarios/tpcqf/suite.yaml \
  --out data/generated/cmp_s1000_sel20 \
  --scale 1000 --selectivity 0.2
```

Keep `--scale`, `--selectivity`, `--timeout`, `--concurrency`, and `--score-mode`
constant across engines. Differences should come from the engines, not the
inputs.

### Fairness considerations

- **Resource limits** — if you compare local containers, give them equal CPU and
  memory (see `docker-compose.cqf-bench.yml` for an example of pinned CPUs and
  memory limits).
- **Warmup** — the suite issues warmup requests before timing; keep
  `warmup_requests` consistent.

## 4. Run all engines in one invocation

`run_benchmark.py` and `execute_tests.py` accept multiple `--filter-engine`
flags, or none (to run all enabled engines). Running them together produces a
single report with every engine as a column group:

```bash
python scripts/execute_tests.py \
  --engines bench/config/local.engines.yaml \
  --generated-data-root data/generated/cmp_s1000_sel20 \
  --filter-engine hapi-cqf-ruler-local \
  --filter-engine mercury-local \
  --out results/cmp_s1000_sel20
```

`mercury-local` is disabled in the default template; remove `disabled` (and
bootstrap the image) before filtering both engines in one run.

## 5. Read the side-by-side matrices

The Markdown report adds a `Result` / `Time` / `Note` column group per engine, so
you can scan a row across engines:

```markdown
## Capability + Performance Matrix

| Scenario | Intent | hapi Result | hapi Time | hapi Note | mercury Result | mercury Time | mercury Note |
|---|---|---|---|---|---|---|---|
| CAP001-P | Count retrieve all of one resource (preload) | PASS | 47.0ms |  | PASS | 31.2ms |  |
| CAP006-I | Retrieve with with-clause join (inline) | PASS | 88.1ms |  | FAIL |  | incorrect result; HTTP 200 |
```

A few interpretation tips:

- Compare **Result first, Time second.** A faster engine that returns the wrong
  answer is not "winning" — its row will be `FAIL` with no time.
- `not executed` means the scenario was skipped for that engine (missing
  capability) — not a failure, but also not a comparison.
- Conformance differences explain capability differences: if an engine fails
  `CONF011`, expect related `Library/$evaluate` capability rows to suffer.

## 6. Keep the comparison reproducible

Each report records the suite hash and git commit. To re-run a comparison later,
use the same suite revision and the same generated data root. Archive the
`results/*.json` files alongside the generated data manifest so others can
reproduce your numbers. See [Publish Results](/cqf-bench/guides/publish-results/).
