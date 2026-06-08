---
title: CLI Reference
description: Every CQF Bench script and its flags.
---

CQF Bench is a set of Python scripts under `scripts/`. Run them from the
repository root with your virtual environment activated. There is no installed
console entry point today — invoke scripts with `python scripts/<name>.py`.

:::note
Defaults below reflect the scripts as written. Where a default points at
`bench/config/engines.example.yaml`, prefer passing your local
`bench/config/local.engines.yaml` explicitly.
:::

## `run_benchmark.py`

Generate payload files (`--run-phase generate`), preload data (`load`), or run
HTTP benchmarks and write reports (`execute`). **`--run-phase` is required.**
The `generate` phase does not read `--engines`.

```bash
# Generate (writes corpus/ + dataset.json under data/generated/…; fixed built-in suite)
python scripts/run_benchmark.py --run-phase generate \
  --scale 100 \
  --selectivity 0.2 \
  --generated-data-root data/generated/payloads_s100_sel20

# Execute (after load_test_data.py or --run-phase load)
python scripts/run_benchmark.py --run-phase execute \
  --engines bench/config/local.engines.yaml \
  --generated-data-root data/generated/payloads_s100_sel20

# Execute a subset of scenarios (repeat --scenario for each id)
python scripts/run_benchmark.py --run-phase execute \
  --engines bench/config/local.engines.yaml \
  --generated-data-root data/generated/payloads_s100_sel20 \
  --scenario CAP001-P --scenario CONF001
```

| Flag | Default | Description |
| --- | --- | --- |
| `--run-phase {generate,load,execute}` | **required** | `generate` = write payloads + `dataset.json`; `load` = preload one tree; `execute` = HTTP benchmark + report (no per-scenario setup when using unified `corpus/setup/` trees). |
| `--engines PATH` | `bench/config/engines.example.yaml` | Engines config (ignored for `generate`). |
| `--suite PATH` | _(see below)_ | Optional override for **load** / **execute** only. **Generate** always uses the built-in suite; `--suite` is ignored with a stderr note. When omitted for load/execute, use `suite_file` from `dataset.json` (legacy trees) or `bench/scenarios/tpcqf/suite.yaml`. |
| `--scale INT` | _(see below)_ | Synthetic patient count. **Required** for **generate**. For **load** / **execute**, read from `dataset.json` when omitted (must exist if `--scale` not passed). |
| `--out PATH` | `results` | Output directory for JSON + Markdown report (`execute` only). |
| `--concurrency INT` | suite default (16) | Concurrent requests per scenario. |
| `--timeout INT` | suite default (30) | Per-request timeout in seconds. |
| `--selectivity FLOAT` | `0.2` | Target fraction of matching rows (0.0–1.0); stored in `dataset.json` for **generate**. |
| `--filter-engine NAME` | _(all)_ | Run only the named engine(s). Repeatable. |
| `--score-mode {compat,strict-2xx}` | `compat` | `compat` uses scenario `expected_http`; `strict-2xx` requires 2xx for setup and main. |
| `--generated-data-root PATH` | _(none)_ | **`generate`:** required output root. **`load`:** required input. **`execute`:** optional inline overrides; when set, `dataset.json` can supply scale (and legacy `suite_file`). |
| `--repetitions INT` | `1` | Repeated execution runs to average timing over (`execute`). |
| `--scenario SCENARIO_ID` | _(all)_ | **Execute only:** run only these scenario id(s); flag is repeatable. Ignored for `load` (stderr note). |

## `generate_scenario_data.py`

Thin wrapper around **`run_benchmark.py --run-phase generate`** (`--out` is the output root).

```bash
python scripts/generate_scenario_data.py \
  --out data/generated/payloads_s100_sel20 \
  --scale 100 --selectivity 0.2
```

| Flag | Default | Description |
| --- | --- | --- |
| `--suite PATH` | _(ignored)_ | Deprecated; generation always uses the built-in benchmark suite. |
| `--out PATH` | **required** | Output directory for generated payloads. |
| `--scale INT` | **required** | Number of synthetic patients. |
| `--selectivity FLOAT` | `0.2` | Target match fraction. |

## `load_test_data.py`

Preload libraries/measures/valuesets and load **all** setup bundles from one generated tree.

```bash
python scripts/load_test_data.py \
  --engines bench/config/local.engines.yaml \
  --generated-data-root data/generated/payloads_s100_sel20 \
  --filter-engine hapi-cqf-ruler-local
```

| Flag | Default | Description |
| --- | --- | --- |
| `--engines PATH` | `bench/config/local.engines.yaml` | Engines config file. |
| `--suite PATH` | _(from dataset.json)_ | Optional; defaults from `dataset.json` in `--generated-data-root`. |
| `--scale INT` | _(from dataset.json)_ | Optional; defaults from `dataset.json`. |
| `--generated-data-root PATH` | **required** | Root of pre-generated payloads (includes `dataset.json`). |
| `--timeout INT` | suite default | Per-request timeout in seconds. |
| `--selectivity FLOAT` | `0.2` | Target match fraction. |
| `--filter-engine NAME` | _(all)_ | Load only for the named engine(s). Repeatable. |
| `--score-mode {compat,strict-2xx}` | `compat` | Scoring mode for setup calls. |

## `execute_tests.py`

Execute the suite against engines without re-running setup.

```bash
python scripts/execute_tests.py \
  --engines bench/config/local.engines.yaml \
  --generated-data-root data/generated/payloads_s100_sel20 \
  --filter-engine hapi-cqf-ruler-local \
  --out results/tpcqf_s100_sel20_execute
```

| Flag | Default | Description |
| --- | --- | --- |
| `--engines PATH` | `bench/config/local.engines.yaml` | Engines config file. |
| `--suite PATH` | _(from dataset.json)_ | Optional when `--generated-data-root` contains `dataset.json`. |
| `--scale INT` | _(from dataset.json)_ | Optional when `dataset.json` is present. |
| `--out PATH` | `results` | Output directory for the report. |
| `--generated-data-root PATH` | _(none)_ | Root of pre-generated payloads (`main` + optional `dataset.json`). |
| `--runs INT` | `5` | Repeated scenario runs, averaged in timing. |
| `--concurrency INT` | suite default | Concurrent requests per scenario. |
| `--timeout INT` | suite default | Per-request timeout in seconds. |
| `--selectivity FLOAT` | `0.2` | Target match fraction. |
| `--filter-engine NAME` | _(all)_ | Run only the named engine(s). Repeatable. |
| `--score-mode {compat,strict-2xx}` | `compat` | Scoring mode. |
| `--scenario SCENARIO_ID` | _(all)_ | Passed through to `run_benchmark.py`; repeatable. |

## `manage_engines.py`

Manage target engines via Docker.

```bash
python scripts/manage_engines.py bootstrap \
  --engines bench/config/local.engines.yaml \
  --engine hapi-cqf-ruler-local
```

**Positional action** (one of):

| Action | Description |
| --- | --- |
| `pull` | Pull the engine image. |
| `build` | Build the engine image. |
| `up` | Start the engine container. |
| `down` | Stop and remove the engine container. |
| `status` | Show container status. |
| `health` | Probe the engine's `health_path`. |
| `bootstrap` | Pull/build as needed, start, and wait for health. |

| Flag | Default | Description |
| --- | --- | --- |
| `--engines PATH` | `bench/config/engines.example.yaml` | Engines config file. |
| `--engine NAME` | _(all Docker-enabled)_ | Apply only to the named engine(s). Repeatable. |

Actions only apply to engines with `docker.enabled: true`; others are skipped.

## `validate_scenarios.py`

Validate a folder-based suite.

```bash
python scripts/validate_scenarios.py --suite bench/scenarios/tpcqf/suite.yaml
```

| Flag | Default | Description |
| --- | --- | --- |
| `--suite PATH` | `bench/scenarios/tpcqf/suite.yaml` | Suite file (or directory). |

Exit codes: `0` = OK, `1` = validation errors, `2` = suite missing/invalid. Also
flags scenario folders that exist on disk but aren't listed in `scenario_ids`.

## `summarize_report.py`

Print a terminal summary of a JSON report.

```bash
python scripts/summarize_report.py results/<run_id>.json
```

| Argument | Description |
| --- | --- |
| `report` | Path to a `results/<run_id>.json` file. |

## `generate_synthetic_data.py`

Generate synthetic benchmark data (lower-level than `generate_scenario_data.py`).

```bash
python scripts/generate_synthetic_data.py --scale 1000 --out data/synthetic_s1000
```

| Flag | Default | Description |
| --- | --- | --- |
| `--patients INT` | _(none)_ | Number of patients (one of `--patients` or `--scale` is required). |
| `--scale INT` | _(none)_ | Alias for `--patients` (benchmark-aligned scale). |
| `--selectivity FLOAT` | `0.2` | Fraction of observations marked as matching (0.0–1.0). |
| `--out PATH` | **required** | Output directory (`patients.ndjson`, `observations.ndjson`). |

## `bootstrap_python_env.sh`

Create the Python virtual environment and install dependencies.

```bash
scripts/bootstrap_python_env.sh --recreate
source .venv/bin/activate
```

| Flag | Description |
| --- | --- |
| `--recreate` | Recreate `.venv` from scratch. |

## `run_scale_matrix.sh`

For each scale, runs **generate → load → execute** (`--score-mode strict-2xx` on
the execute step) so every scale uses a matching generated payload tree under
`data/generated/scale_matrix_s<scale>_sel20`.

```bash
# Default scales: 100, 10000, 1000000
scripts/run_scale_matrix.sh

# Custom scales (positional arguments)
scripts/run_scale_matrix.sh 100 1000 10000
```

Environment variables (optional):

| Variable | Default | Description |
| --- | --- | --- |
| `ENGINES_FILE` | `bench/config/engines.example.yaml` | Engines config passed to `run_benchmark.py`. |
