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

Run a CQF engine comparison benchmark (setup and/or execute).

```bash
python scripts/run_benchmark.py --scale 100 \
  --engines bench/config/local.engines.yaml \
  --suite bench/scenarios/tpcqf/suite.yaml
```

| Flag | Default | Description |
| --- | --- | --- |
| `--engines PATH` | `bench/config/engines.example.yaml` | Engines config file. |
| `--suite PATH` | `bench/scenarios/tpcqf/suite.yaml` | Suite file (or directory containing `suite.yaml`). |
| `--scale INT` | **required** | Number of synthetic patients. |
| `--out PATH` | `results` | Output directory for the JSON + Markdown report. |
| `--concurrency INT` | suite default (16) | Concurrent requests per scenario. |
| `--timeout INT` | suite default (30) | Per-request timeout in seconds. |
| `--selectivity FLOAT` | `0.2` | Target fraction of matching rows (0.0–1.0). |
| `--filter-engine NAME` | _(all)_ | Run only the named engine(s). Repeatable. |
| `--score-mode {compat,strict-2xx}` | `compat` | `compat` uses scenario `expected_http`; `strict-2xx` requires 2xx for setup and main. |
| `--run-phase {full,load,execute}` | `full` | `full` = setup + execute; `load` = preload only; `execute` = run only (no setup). |
| `--generated-data-root PATH` | _(none)_ | Root of pre-generated payloads from `generate_scenario_data.py`. |
| `--repetitions INT` | `1` | Repeated execution runs to average timing over. |

## `generate_scenario_data.py`

Generate per-scenario payload files ahead of execution (deterministic).

```bash
python scripts/generate_scenario_data.py \
  --suite bench/scenarios/tpcqf/suite.yaml \
  --out data/generated/payloads_s100_sel20 \
  --scale 100 --selectivity 0.2 --phase both
```

| Flag | Default | Description |
| --- | --- | --- |
| `--suite PATH` | `bench/scenarios/tpcqf/suite.yaml` | Suite file. |
| `--out PATH` | **required** | Output directory for generated payloads. |
| `--scale INT` | **required** | Number of synthetic patients. |
| `--selectivity FLOAT` | `0.2` | Target match fraction. |
| `--phase {setup,main,both}` | `setup` | Which payload phase(s) to generate. |
| `--scenario ID` | _(all)_ | Limit to specific scenario ID(s). Repeatable. |

## `load_test_data.py`

Preload libraries/measures/valuesets and load setup data into engines.

```bash
python scripts/load_test_data.py \
  --engines bench/config/local.engines.yaml \
  --suite bench/scenarios/tpcqf/suite.yaml \
  --scale 100 \
  --generated-data-root data/generated/payloads_s100_sel20 \
  --filter-engine hapi-cqf-ruler-local
```

| Flag | Default | Description |
| --- | --- | --- |
| `--engines PATH` | `bench/config/local.engines.yaml` | Engines config file. |
| `--suite PATH` | `bench/scenarios/tpcqf/suite.yaml` | Suite file. |
| `--scale INT` | **required** | Number of synthetic patients. |
| `--generated-data-root PATH` | **required** | Root of pre-generated payloads. |
| `--timeout INT` | suite default | Per-request timeout in seconds. |
| `--selectivity FLOAT` | `0.2` | Target match fraction. |
| `--filter-engine NAME` | _(all)_ | Load only for the named engine(s). Repeatable. |
| `--score-mode {compat,strict-2xx}` | `compat` | Scoring mode for setup calls. |

## `execute_tests.py`

Execute the suite against engines without re-running setup.

```bash
python scripts/execute_tests.py \
  --engines bench/config/local.engines.yaml \
  --suite bench/scenarios/tpcqf/suite.yaml \
  --scale 100 \
  --generated-data-root data/generated/payloads_s100_sel20 \
  --filter-engine hapi-cqf-ruler-local \
  --out results/tpcqf_s100_sel20_execute
```

| Flag | Default | Description |
| --- | --- | --- |
| `--engines PATH` | `bench/config/local.engines.yaml` | Engines config file. |
| `--suite PATH` | `bench/scenarios/tpcqf/suite.yaml` | Suite file. |
| `--scale INT` | **required** | Number of synthetic patients. |
| `--out PATH` | `results` | Output directory for the report. |
| `--generated-data-root PATH` | _(none)_ | Root of pre-generated payloads (used to inject inline `main` payloads). |
| `--runs INT` | `5` | Repeated scenario runs, averaged in timing. |
| `--concurrency INT` | suite default | Concurrent requests per scenario. |
| `--timeout INT` | suite default | Per-request timeout in seconds. |
| `--selectivity FLOAT` | `0.2` | Target match fraction. |
| `--filter-engine NAME` | _(all)_ | Run only the named engine(s). Repeatable. |
| `--score-mode {compat,strict-2xx}` | `compat` | Scoring mode. |

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

Convenience wrapper that runs `run_benchmark.py` once per scale with
`--score-mode strict-2xx`.

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
| `SUITE_FILE` | `bench/scenarios/tpcqf/suite.yaml` | Suite file passed to `run_benchmark.py`. |
