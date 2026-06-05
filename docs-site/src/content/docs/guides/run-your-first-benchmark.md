---
title: Run Your First Benchmark
description: A detailed walkthrough of generating data, loading it, executing the suite, and reading the report.
---

This guide walks through a complete benchmark run against a single engine, with
explanations of what each step does and how to verify it. It assumes you have
completed [Installation](/cqf-bench/installation/).

## Goal

Run the `TPCQF` suite at scale 100 against HAPI CQF Ruler, and produce a report
you can read.

## Step 0 — Activate your environment

```bash
cd cqf-bench
source .venv/bin/activate
```

If `.venv` doesn't exist yet, run `scripts/bootstrap_python_env.sh --recreate`
first.

## Step 1 — Confirm the engine is healthy

```bash
python scripts/manage_engines.py health \
  --engines bench/config/local.engines.yaml \
  --engine hapi-cqf-ruler-local
```

Expect HTTP `200` from the engine's `health_path`
(`http://localhost:8081/fhir/metadata`). If it isn't up:

```bash
python scripts/manage_engines.py bootstrap \
  --engines bench/config/local.engines.yaml \
  --engine hapi-cqf-ruler-local
```

## Step 2 — Validate the suite

A quick structural check before spending time on a run:

```bash
python scripts/validate_scenarios.py --suite bench/scenarios/tpcqf/suite.yaml
```

You should see `Scenario validation OK: <N> scenarios ...`.

## Step 3 — Generate deterministic data

```bash
python scripts/generate_scenario_data.py \
  --suite bench/scenarios/tpcqf/suite.yaml \
  --out data/generated/scenario_payloads_s100_sel20 \
  --scale 100 \
  --selectivity 0.2 \
  --phase both
```

What this does:

- Builds FHIR payloads for each data-backed scenario from its `match.fsh` /
  `variations.fsh` templates and `mutator.yaml`.
- `--scale 100` generates data for 100 synthetic patients (`p1`…`p100`).
- `--selectivity 0.2` makes ~20% of generated resources match each scenario's
  logic.
- `--phase both` produces preload (`setup`) payloads for `-P` scenarios and
  request-time (`main`) payloads for `-I` scenarios.

The generator is deterministic: the same `--scale` and `--selectivity` produce
the same data every time, so result counts are stable.

## Step 4 — Load data into the engine

```bash
python scripts/load_test_data.py \
  --engines bench/config/local.engines.yaml \
  --suite bench/scenarios/tpcqf/suite.yaml \
  --scale 100 \
  --generated-data-root data/generated/scenario_payloads_s100_sel20 \
  --filter-engine hapi-cqf-ruler-local
```

This preloads the libraries, measures, and valuesets the suite references, then
loads each `-P` scenario's generated setup data into the server. The console
prints a setup pass rate per scenario; investigate anything below `1.000` before
trusting execution results.

## Step 5 — Execute the suite

```bash
python scripts/execute_tests.py \
  --engines bench/config/local.engines.yaml \
  --suite bench/scenarios/tpcqf/suite.yaml \
  --scale 100 \
  --generated-data-root data/generated/scenario_payloads_s100_sel20 \
  --filter-engine hapi-cqf-ruler-local \
  --out results/tpcqf_s100_sel20_execute \
  --runs 5
```

- `-I` scenarios inject their generated `main` payloads at request time.
- `--runs 5` repeats each scenario five times and averages the timing.
- No setup is re-run; execution uses the data loaded in Step 4.

## One-shot alternative

To do load + execute together without managing the generate step yourself:

```bash
python scripts/run_benchmark.py \
  --engines bench/config/local.engines.yaml \
  --suite bench/scenarios/tpcqf/suite.yaml \
  --scale 100 \
  --filter-engine hapi-cqf-ruler-local
```

Use `--run-phase load` or `--run-phase execute` to split the phases, and
`--generated-data-root` to consume pre-generated payloads.

## Step 6 — Read the report

The run writes `results/<run_id>.json` and `results/<run_id>.md`. Open the
Markdown file for the conformance and capability matrices, or summarize the JSON:

```bash
python scripts/summarize_report.py results/<run_id>.json
```

Interpreting results:

- **Conformance** rows are PASS/FAIL by HTTP class — they tell you which
  operations the engine exposes correctly.
- **Capability** rows are PASS only when the response is both successful and
  correct; timing appears only on PASS.
- A `FAIL` note such as `incorrect result` means the engine returned a success
  status but the wrong answer.

See [Results](/cqf-bench/concepts/results/) and
[Output Format](/cqf-bench/reference/output-format/) for details.

## Scaling up

Once a small run is clean, increase `--scale` (e.g. `1000`, `10000`) to observe
how latency grows. Generate once at the target scale, load once, then execute as
many times as you like. The helper `scripts/run_scale_matrix.sh` is a convenient
starting point for sweeping multiple scales.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| Setup pass rate `< 1.000` | Engine rejected preload; check the printed HTTP status and body. |
| Capability rows all `unsupported` | Engine lacks the operation or the required capability tag is missing. |
| `incorrect result` notes | CQL evaluated but returned an unexpected value — check selectivity and validators. |
| `not executed` in the matrix | Scenario was skipped for that engine (missing capability) or the run was filtered. |
