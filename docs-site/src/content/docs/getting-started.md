---
title: Getting Started
description: Run CQF Bench end to end against the open-source HAPI CQF Ruler engine.
---

This is a minimal quickstart for running CQF Bench against the open-source
**HAPI CQF Ruler** engine. By the end you will have generated synthetic data,
loaded it into a running engine, executed the suite, and produced a report.

If you have not set up prerequisites yet, see [Installation](/cqf-bench/installation/)
first. This quickstart uses [HAPI CQF Ruler](/cqf-bench/engines/hapi-cqf-ruler/);
to benchmark another server, see [Engine guides](/cqf-bench/engines/).

## 1. Create your local config

CQF Bench keeps machine-specific values out of version control. Copy the tracked
templates into local, gitignored files:

```bash
cp bench/config/engines.example.yaml bench/config/local.engines.yaml
cp docker-compose.override.yml.example docker-compose.override.yml
```

`bench/config/local.engines.yaml` and `docker-compose.override.yml` are
gitignored and are where your real values live. The localhost endpoints in the
example file are valid defaults for local runs.

## 2. Stand up HAPI CQF Ruler

From the repository root, bootstrap and health-check the engine container:

```bash
python scripts/manage_engines.py bootstrap \
  --engines bench/config/local.engines.yaml \
  --engine hapi-cqf-ruler-local

python scripts/manage_engines.py health \
  --engines bench/config/local.engines.yaml \
  --engine hapi-cqf-ruler-local
```

A healthy engine returns HTTP `200` from `http://localhost:8081/fhir/metadata`.

## 3. Bootstrap the Python environment

```bash
scripts/bootstrap_python_env.sh --recreate
source .venv/bin/activate
```

The only runtime dependency is PyYAML; the bootstrap script creates a virtual
environment and installs it.

## 4. Run the three-step flow

CQF Bench separates **generate → load → execute** so you can preload data once
and execute the suite many times without regenerating or reloading.

### 4.1 Generate data (scale 100, selectivity 20%)

```bash
python scripts/generate_scenario_data.py \
  --suite bench/scenarios/tpcqf/suite.yaml \
  --out data/generated/scenario_payloads_s100_sel20 \
  --scale 100 \
  --selectivity 0.2
```

- `--suite` points at the folder-based benchmark definition (`suite.yaml` plus
  scenario folders); it drives mutators, FSH templates, and payload shapes.
- `--scale` is the number of synthetic patients.
- `--selectivity` is the fraction of generated data that should match the
  scenario logic (default `0.2`).
- The output directory receives **all** `setup` and `main` JSON for every
  scenario, plus `dataset.json` (suite path, scale, selectivity). See
  `bench/DATA_LAYOUT.md` in the repository for the full tree layout.

### 4.2 Load setup data into the engine

```bash
python scripts/load_test_data.py \
  --engines bench/config/local.engines.yaml \
  --generated-data-root data/generated/scenario_payloads_s100_sel20 \
  --filter-engine hapi-cqf-ruler-local
```

This preloads required libraries, measures, and valuesets, then loads **all**
generated setup bundles from that tree. `dataset.json` supplies `suite_file`
and `scale` when you omit `--suite` / `--scale`.

### 4.3 Execute the suite

```bash
python scripts/execute_tests.py \
  --engines bench/config/local.engines.yaml \
  --generated-data-root data/generated/scenario_payloads_s100_sel20 \
  --filter-engine hapi-cqf-ruler-local \
  --out results/tpcqf_s100_sel20_execute
```

Inline (`CAP###-I`) scenarios inject their generated `main` payloads from
`--generated-data-root` at request time. `execute_tests.py` defaults to
`--runs 5`, repeating each scenario for averaged timing.

## Alternative: `run_benchmark.py` for every phase

The same three phases map directly to **`--run-phase`** (required on
`run_benchmark.py`):

```bash
python scripts/run_benchmark.py --run-phase generate \
  --suite bench/scenarios/tpcqf/suite.yaml \
  --scale 100 \
  --selectivity 0.2 \
  --generated-data-root data/generated/smoke_s100_sel20

python scripts/run_benchmark.py --run-phase load \
  --engines bench/config/local.engines.yaml \
  --generated-data-root data/generated/smoke_s100_sel20 \
  --filter-engine hapi-cqf-ruler-local

python scripts/run_benchmark.py --run-phase execute \
  --engines bench/config/local.engines.yaml \
  --generated-data-root data/generated/smoke_s100_sel20 \
  --filter-engine hapi-cqf-ruler-local \
  --out results/smoke_s100_sel20
```

`generate` ignores `--engines`. `load` / `execute` read `dataset.json` when
`--suite` / `--scale` are omitted.

## Read the report

Each run writes two files:

- `results/<run_id>.json` — the full machine-readable report.
- `results/<run_id>.md` — a Markdown summary with conformance and capability
  matrices.

`<run_id>` is `<suite_id>_<scale>_<random_suffix>`. For a quick terminal summary
of a JSON report:

```bash
python scripts/summarize_report.py results/<run_id>.json
```

See [Output Format](/cqf-bench/reference/output-format/) for the full schema.

## Next steps

- [Run Your First Benchmark](/cqf-bench/guides/run-your-first-benchmark/) — a more
  detailed walkthrough.
- [Compare Engines](/cqf-bench/guides/compare-engines/) — run the same suite
  against multiple engines.
- [CLI Reference](/cqf-bench/reference/cli/) — every script and flag.
