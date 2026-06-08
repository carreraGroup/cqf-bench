---
title: HAPI CQF Ruler
description: Run CQF Bench against the open-source HAPI CQF Ruler Docker image — the recommended local engine for first benchmarks and release comparisons.
---

**HAPI CQF Ruler** is an open-source CQF server packaged as Docker
(`alphora/cqf-ruler`). CQF Bench ships a ready-made config entry and a dedicated
**`hapi-cqf-ruler`** adapter so the TPCQF suite runs without hand-editing
scenario paths for HAPI's GET/POST and instance-level operation conventions.

This is the engine used in [Getting Started](/cqf-bench/getting-started/) and
the recommended target for **release benchmarks** until additional product guides
(e.g. Mercury) are published.

## Template entry

In `bench/config/engines.example.yaml` the engine is named
**`hapi-cqf-ruler-local`**:

| Setting | Value |
| --- | --- |
| `adapter` | `hapi-cqf-ruler` |
| `base_url` | `http://localhost:8081` |
| `cqf_base_path` / `fhir_base_path` / `data_base_path` | `/fhir` |
| Docker image | `alphora/cqf-ruler:latest` |
| Host port | `8081` → container `8080` |
| Suggested local fairness caps | `cpus: 4.0`, `mem_limit: 8g`, `cpuset: "0-3"` |
| Health check | `GET http://localhost:8081/fhir/metadata` |

Copy the template to your local config:

```bash
cp bench/config/engines.example.yaml bench/config/local.engines.yaml
```

## Start the server

Requires Docker. From the repository root:

```bash
python scripts/manage_engines.py bootstrap \
  --engines bench/config/local.engines.yaml \
  --engine hapi-cqf-ruler-local
```

`bootstrap` pulls the image (unless configured otherwise), starts the container,
and probes `health_path`.

Verify:

```bash
python scripts/manage_engines.py health \
  --engines bench/config/local.engines.yaml \
  --engine hapi-cqf-ruler-local
```

Expect HTTP `200` from `http://localhost:8081/fhir/metadata`.

Other useful actions:

```bash
python scripts/manage_engines.py status --engines bench/config/local.engines.yaml --engine hapi-cqf-ruler-local
python scripts/manage_engines.py down   --engines bench/config/local.engines.yaml --engine hapi-cqf-ruler-local
```

## Declared capabilities

The template enables:

- `resident_data_load`
- `resident_execute`
- `system_cql`
- `inline_bundle_execute`

That covers preload (`CAP###-P`) and inline (`CAP###-I`) capability scenarios plus
conformance operations the suite expects on a full CQF Ruler surface. If you run
an older or trimmed image, remove capabilities you know are unsupported so
skipped rows reflect reality.

## What the `hapi-cqf-ruler` adapter does

Scenarios are written in an engine-neutral shape. The adapter applies HAPI-specific
rewrites at run time:

- **GET → POST** for `/Library/$evaluate` and `/Measure/$evaluate-measure` when
  the scenario specifies GET — query parameters become a `Parameters` body.
- **Type-level → instance-level paths** — e.g. `/Library/$evaluate` becomes
  `/Library/{id}/$evaluate` when a library id is known, and measure operations
  similarly use `/Measure/{id}/$…`.
- **Parameter cleanup** — drops redundant `library` / `measure` parameters from
  the body after paths are rewritten to avoid canonical mismatches.
- **Setup data POST** — for `path_role: data` setup calls, posts to `/` on the
  data base path as Ruler expects.

You should not fork scenarios for HAPI; keep changes in the adapter. Details:
[Engine Adapters](/cqf-bench/concepts/engine-adapters/#what-adapters-do-in-practice).

## Run the benchmark

With Python env active (`scripts/bootstrap_python_env.sh`):

```bash
python scripts/run_benchmark.py \
  --run-phase execute \
  --engines bench/config/local.engines.yaml \
  --suite bench/scenarios/tpcqf/suite.yaml \
  --scale 100 \
  --filter-engine hapi-cqf-ruler-local
```

For generate → load → execute as separate steps, follow
[Getting Started](/cqf-bench/getting-started/#4-run-the-three-step-flow) or
[Run Your First Benchmark](/cqf-bench/guides/run-your-first-benchmark/).

Reports: `results/<run_id>.json` and `results/<run_id>.md`.

## Compare against other engines

Use the same generated data root and include multiple `--filter-engine` flags.
See [Compare Engines](/cqf-bench/guides/compare-engines/).

## Container environment

The template sets:

```yaml
env:
  hapi.fhir.cql_enabled: 'true'
```

Adjust `docker.env` in your local file if your image documents additional
variables. Pin the image tag (instead of `:latest`) when publishing reproducible
results, and record the digest in your results bundle
([Publish Results](/cqf-bench/guides/publish-results/)).

For fair local comparisons, keep HAPI and Mercury on the same CPU and memory
limits in `local.engines.yaml`; `manage_engines.py` now applies `cpus`,
`mem_limit`, `mem_reservation`, and `cpuset` directly to `docker run`.

## Troubleshooting

| Symptom | Things to check |
| --- | --- |
| `health FAILED` / connection refused | Container not running; port `8081` in use by another process. |
| Many `not executed` | Missing capabilities in YAML vs what the image supports. |
| Conformance `UNSUPPORTED` / `WARNING` | Expected for unimplemented ops — compare across engines, not only HAPI. |
| Capability `FAIL` with HTTP 200 | CQL correctness — see scenario `expected.yaml`, not adapter config. |
| Pull errors | Registry access; try `docker pull alphora/cqf-ruler:latest` manually. |

Port conflict with another engine? Default ports in the template: Mercury
`8080`, HAPI CQF Ruler `8081` — only run simultaneous containers if each port is free.

## Observed behavior (May 28, 2026)

These notes are intentionally engine-specific and should be read as
implementation observations, not framework rules.

- In full `TPCQF` runs, HAPI often returns HTTP `200` for `CAP` scenarios but
  still fails correctness validation (wrong result content/shape). This is
  scored as `FAIL` by design.
- `CAP002` and `CAP003` track together (same pass/fail pattern) in recent runs,
  which is expected when they exercise the same value set semantics over the
  same data.
- During some local runs, the container showed startup/restart instability
  (`connection reset by peer`) around benchmark execution windows. Treat those
  runs as transport-invalid and re-run after health stabilizes.

For reproducible comparisons, record:

1. exact suite phases (`generate` / `load` / `execute`) and whether payloads came from `--generated-data-root`,
2. scale/concurrency/timeout,
3. image tag and digest,
4. report JSON artifacts.

## Remote HAPI / non-Docker

To benchmark a Ruler instance you do not start via `manage_engines.py`:

1. Copy the `hapi-cqf-ruler-local` block to a new `name`.
2. Set `base_url` to your reachable host.
3. Set `docker.enabled: false`.
4. Keep `adapter: hapi-cqf-ruler` so request rewriting still applies.

See also [Add an engine](/cqf-bench/guides/add-an-engine/) for headers, tokens,
and capability tuning.

## Related

- [Engine guides](/cqf-bench/engines/) — index of product setup pages
- [Add an engine](/cqf-bench/guides/add-an-engine/) — BYO / custom endpoints
- [Compare Engines](/cqf-bench/guides/compare-engines/) — side-by-side matrices
