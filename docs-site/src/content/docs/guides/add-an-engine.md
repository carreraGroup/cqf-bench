---
title: Add an Engine
description: Register a CQF or Clinical Reasoning server in CQF Bench so it runs in the same suite and reports as every other engine.
---

Use this guide when you want CQF Bench to **include your server in a comparison** —
whether it is a local Docker container, a shared dev environment, or a vendor
hosted endpoint.

Product-specific walkthroughs (less YAML guesswork) live under
[Engine guides](/cqf-bench/engines/). Today that includes
[HAPI CQF Ruler](/cqf-bench/engines/hapi-cqf-ruler/); more pages (e.g. Mercury)
will be added over time.

## 1. Decide: config only or new adapter?

| Situation | What to do |
| --- | --- |
| Server already accepts scenario paths/methods as written, or only needs different `base_url` / headers | Add a config entry with `adapter: generic-cqf`. |
| Server needs GET→POST promotion, instance-level operation paths, canonical cleanup, or bundle reshaping | Use an existing adapter if one matches (see [Engine Adapters](/cqf-bench/concepts/engine-adapters/)), or implement a new adapter in `scripts/run_benchmark.py`. |

Most **remote** or **vendor** endpoints start with `generic-cqf` and an honest
`capabilities` list. Tune until skipped scenarios match what the server truly
supports, then add an adapter only for behavior the harness cannot express in YAML.

## 2. Create your local engines config

```bash
cp bench/config/engines.example.yaml bench/config/local.engines.yaml
```

`local.engines.yaml` is gitignored. Never commit secrets; use `${ENV_VAR}` in
headers (see [Configuration Reference](/cqf-bench/reference/configuration/#secrets-via-environment-variables)).

## 3. Add an engine block

Append (or uncomment) an entry with a **unique** `name` — this is what
`--filter-engine` and report column headers use.

```yaml
engines:
  - name: my-cqf-server
    adapter: generic-cqf
    base_url: https://cqf.example.org
    cqf_base_path: /fhir
    fhir_base_path: /fhir
    data_base_path: /fhir
    headers:
      Authorization: Bearer ${ENGINE_BEARER_TOKEN}
    capabilities:
      - resident_data_load
      - resident_execute
      - inline_bundle_execute
      - system_cql
    docker:
      enabled: false
      image: ''
      container_name: ''
      host_port: 0
      container_port: 0
      env: {}
      health_path: /fhir/metadata
```

### Path fields

| Field | Purpose |
| --- | --- |
| `base_url` | Scheme, host, and port only (no path suffix). |
| `cqf_base_path` | Prefix for CQF operation URLs (`$evaluate`, `$evaluate-measure`, …). |
| `fhir_base_path` | Prefix for loading Libraries, Measures, ValueSets during setup. |
| `data_base_path` | Prefix for resident data loads (often the same as `fhir_base_path`). |

If your server mounts everything under `/fhir`, set all three to `/fhir` (as
HAPI CQF Ruler does). If CQF lives under `/cqf` and FHIR under `/fhir`, split
them accordingly (see the Mercury entry in `engines.example.yaml`).

### Capabilities (be accurate)

Capabilities **gate** scenarios. If you declare a capability the server does not
really support, you will get `FAIL` rows; if you omit one it supports, scenarios
will show `not executed` instead of measuring that feature.

| Capability | Declare when… |
| --- | --- |
| `resident_data_load` | Setup can preload Patient/Condition (etc.) into the server. |
| `resident_execute` | `$evaluate` / measure ops can run against resident data. |
| `inline_bundle_execute` | Operations accept inline `Bundle` / payload data (`CAP###-I`). |
| `system_cql` | System-level `$cql` is supported. |
| `library_write_once_execute_many` | Library can be stored once and evaluated repeatedly. |

When in doubt, start with a minimal set, run a small scale, and expand as
conformance rows go green.

### Local Docker vs remote endpoint

**Docker-managed** (like HAPI CQF Ruler in the template):

```yaml
docker:
  enabled: true
  image: your-org/your-cqf-image:tag
  container_name: my-cqf-bench
  host_port: 8083
  container_port: 8080
  cpus: 4.0
  mem_limit: 8g
  cpuset: "0-3"
  env: {}
  health_path: /fhir/metadata
```

Use `manage_engines.py` to pull/start and probe health:

```bash
python scripts/manage_engines.py bootstrap \
  --engines bench/config/local.engines.yaml \
  --engine my-cqf-server
```

**Remote / BYO hosting** — set `docker.enabled: false` and ensure the URL is
reachable from where you run CQF Bench. You are responsible for lifecycle and
resource limits; CQF Bench only issues HTTP requests.

To disable an entry without deleting it:

```yaml
disabled: true
disabled_reason: Waiting for QA environment URL
```

## 4. Verify connectivity

```bash
python scripts/manage_engines.py health \
  --engines bench/config/local.engines.yaml \
  --engine my-cqf-server
```

For Docker-disabled engines, `health` still GETs
`base_url` + `docker.health_path` — set `health_path` to a stable metadata or
health route.

## 5. Run a smoke benchmark

```bash
source .venv/bin/activate   # after bootstrap_python_env.sh

python scripts/run_benchmark.py \
  --engines bench/config/local.engines.yaml \
  --suite bench/scenarios/tpcqf/suite.yaml \
  --scale 100 \
  --filter-engine my-cqf-server
```

Inspect `results/<run_id>.md`:

- Many `not executed` rows → revisit **capabilities**.
- Conformance `FAIL` on specific operations → server gap or wrong paths/adapter.
- Capability `FAIL` with HTTP 200 → correctness issue (validators), not config.

## 6. Add to a multi-engine comparison

Once the smoke run looks right, include your engine alongside others. See
[Compare Engines](/cqf-bench/guides/compare-engines/).

```bash
python scripts/execute_tests.py \
  --engines bench/config/local.engines.yaml \
  --suite bench/scenarios/tpcqf/suite.yaml \
  --scale 1000 \
  --generated-data-root data/generated/cmp_s1000_sel20 \
  --filter-engine hapi-cqf-ruler-local \
  --filter-engine my-cqf-server \
  --out results/cmp_s1000_sel20
```

## 7. Implement a new adapter (optional)

When `generic-cqf` is not enough:

1. Subclass `EngineAdapter` in `scripts/run_benchmark.py` (see
   `HapiCqfRulerAdapter` / `MercuryCqfAdapter` for patterns).
2. Register it in the `ADAPTERS` dict.
3. Set `adapter: your-adapter-name` in the engine entry.
4. Document behavior on a new page under `docs-site/src/content/docs/engines/`
   and add it to the sidebar in `astro.config.mjs`.

Contribution expectations: [Contributing](/cqf-bench/contributing/#adding-an-engine-adapter).

## Related

- [Engine guides](/cqf-bench/engines/) — product-specific setup index
- [HAPI CQF Ruler](/cqf-bench/engines/hapi-cqf-ruler/) — reference Docker engine for release runs
- [Configuration Reference](/cqf-bench/reference/configuration/) — full YAML schema
