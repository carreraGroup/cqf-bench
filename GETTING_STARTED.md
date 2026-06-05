# Getting Started

This is a minimal quickstart for running `cqf-bench` with the open-source CQF Ruler engine.

## Fast Smoke Test

Use this path to verify the harness, engine startup, data generation, and report
generation end to end against the public reference engine (HAPI CQF Ruler).

**Expected time:** ~10–15 minutes on a typical developer machine (most of it is the
first Docker image pull and engine startup).

**Requirements:** Docker running, Python 3.11+, ports `8081` free.

```bash
cd cqf-bench

# 0) Local config from tracked templates
cp bench/config/engines.example.yaml bench/config/local.engines.yaml
cp docker-compose.override.yml.example docker-compose.override.yml

# 1) Start the reference engine and confirm health
python scripts/manage_engines.py bootstrap --engines bench/config/local.engines.yaml --engine hapi-cqf-ruler-local
python scripts/manage_engines.py health    --engines bench/config/local.engines.yaml --engine hapi-cqf-ruler-local

# 2) Python environment
scripts/bootstrap_python_env.sh --recreate
source .venv/bin/activate

# 3) Generate -> load -> execute a small run
python scripts/generate_scenario_data.py \
  --suite bench/scenarios/tpcqf/suite.yaml \
  --out data/generated/smoke_s100_sel20 \
  --scale 100 --selectivity 0.2 --phase both
python scripts/load_test_data.py \
  --engines bench/config/local.engines.yaml --suite bench/scenarios/tpcqf/suite.yaml \
  --scale 100 --generated-data-root data/generated/smoke_s100_sel20 \
  --filter-engine hapi-cqf-ruler-local
python scripts/execute_tests.py \
  --engines bench/config/local.engines.yaml --suite bench/scenarios/tpcqf/suite.yaml \
  --scale 100 --generated-data-root data/generated/smoke_s100_sel20 \
  --filter-engine hapi-cqf-ruler-local \
  --out results/smoke_s100_sel20
```

Expected: the health step returns HTTP `200` for `http://localhost:8081/fhir/metadata`,
and the run writes a report pair:

```
results/<run_id>.json
results/<run_id>.md
```

Open the `.md` report — conformance and capability matrices use `PASS` / `FAIL` /
`UNSUPPORTED` / `NOT_RUN` (see the status legend at the top of the report). For a
preview of what a report looks like before you run anything, see
[examples/reports/](examples/reports/).

If a step fails, the most common causes are: port `8081` already in use, Docker not
running, the image still pulling, or the engine not yet healthy — re-run the `health`
command and wait for `200` before continuing.

The sections below explain each step in more detail.

## Local config files

Use the tracked examples as templates:

```bash
cp bench/config/engines.example.yaml bench/config/local.engines.yaml
cp docker-compose.override.yml.example docker-compose.override.yml
```

`bench/config/local.engines.yaml` and `docker-compose.override.yml` are local-only and gitignored.
Example files may use localhost endpoints, which are valid defaults for local runs.

## 1) Stand up CQF Ruler (Docker)

From repo root:

```bash
cd cqf-bench
python scripts/manage_engines.py bootstrap --engines bench/config/local.engines.yaml --engine hapi-cqf-ruler-local
python scripts/manage_engines.py health --engines bench/config/local.engines.yaml --engine hapi-cqf-ruler-local
```

Expected: health returns HTTP `200` for `http://localhost:8081/fhir/metadata`.

## 2) Bootstrap Python environment

```bash
cd cqf-bench
scripts/bootstrap_python_env.sh --recreate
source .venv/bin/activate
```

## 3) Run the 3-step benchmark flow

### 3.1 Generate data (scale 100, selectivity 20%)

```bash
python scripts/generate_scenario_data.py \
  --suite bench/scenarios/tpcqf/suite.yaml \
  --out data/generated/scenario_payloads_s100_sel20 \
  --scale 100 \
  --selectivity 0.2 \
  --phase both
```

### 3.2 Load generated setup data into engine (preload only)

```bash
python scripts/load_test_data.py \
  --engines bench/config/local.engines.yaml \
  --suite bench/scenarios/tpcqf/suite.yaml \
  --scale 100 \
  --generated-data-root data/generated/scenario_payloads_s100_sel20 \
  --filter-engine hapi-cqf-ruler-local
```

### 3.3 Execute tests (no setup reload)

Inline tests (`CAP###-I`) will inject generated `main` payloads from `--generated-data-root`.

```bash
python scripts/execute_tests.py \
  --engines bench/config/local.engines.yaml \
  --suite bench/scenarios/tpcqf/suite.yaml \
  --scale 100 \
  --generated-data-root data/generated/scenario_payloads_s100_sel20 \
  --filter-engine hapi-cqf-ruler-local \
  --out results/tpcqf_s100_sel20_execute
```

Report outputs:

- `results/<run_id>.json`
- `results/<run_id>.md`
