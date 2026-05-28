---
title: Publish Results
description: Share reproducible benchmark results that others can verify and re-run.
---

A benchmark number is only useful if someone else can reproduce it. This guide
covers how to package and publish CQF Bench results so they're trustworthy and
re-runnable.

## What makes a result reproducible

Every report already captures the provenance you need:

- `suite_id`, `suite_file`, and `suite_hash` (a hash over all scenario files),
- the `git_commit` of the harness at run time,
- the run parameters — `scale`, `selectivity` (via the generated data root),
  `concurrency`, `timeout_seconds`, `score_mode`, `repetitions`,
- timestamps and `duration_seconds`.

Two reports with the same `suite_hash` and `git_commit` were produced from the
same suite and harness, so any difference is attributable to the engine or
environment.

## Recommended publishing bundle

When you publish results, include:

1. **The JSON report(s)** — `results/<run_id>.json`. This is the source of truth.
2. **The Markdown summary** — `results/<run_id>.md`, for human readers.
3. **The exact commands** you ran (generate / load / execute), including
   `--scale`, `--selectivity`, and `--score-mode`.
4. **Engine identification** — image tags or versions for each engine
   (e.g. `alphora/cqf-ruler:latest` resolved to a digest), and host resource
   limits if relevant.
5. **The git commit** of CQF Bench (already in the report, but call it out).

If your organization maintains a separate results archive or dashboard, link to
it here and describe how it maps to `results/<run_id>.json` in this repo.

## Generating a clean, comparable run

```bash
# Pin the data so the run is reproducible.
python scripts/generate_scenario_data.py \
  --suite bench/scenarios/tpcqf/suite.yaml \
  --out data/generated/pub_s1000_sel20 \
  --scale 1000 --selectivity 0.2 --phase both

python scripts/load_test_data.py \
  --engines bench/config/local.engines.yaml \
  --suite bench/scenarios/tpcqf/suite.yaml \
  --scale 1000 \
  --generated-data-root data/generated/pub_s1000_sel20

python scripts/execute_tests.py \
  --engines bench/config/local.engines.yaml \
  --suite bench/scenarios/tpcqf/suite.yaml \
  --scale 1000 \
  --generated-data-root data/generated/pub_s1000_sel20 \
  --out results/pub_s1000_sel20 \
  --runs 5
```

Capture the engine image digests you used, for example:

```bash
docker image inspect alphora/cqf-ruler:latest --format '{{ index .RepoDigests 0 }}'
```

## Note on data and privacy

All CQF Bench fixtures are **synthetic and generated** — no patient data is
involved. The generated data root is reproducible from `--scale` and
`--selectivity`, so you generally don't need to publish the data itself; the
generation command is enough. If you do attach data, confirm it contains only
generated synthetic resources.

By default the repository gitignores `results/` and `data/generated/`, so you
publish results deliberately rather than committing them by accident.

## Publishing alongside the docs

Because this documentation site is static and lives in
[`docs-site/`](https://github.com/carreraGroup/cqf-bench/tree/main/docs-site), you
can add a results page or a "latest run" table under `src/content/docs/` and
refresh it from CI when you are ready to automate publishing.

## Comparing published results over time

To track regressions across harness or engine versions:

- Keep each published run's JSON keyed by `run_id` (which already encodes suite
  and scale).
- Diff `latency_ms` percentiles and `PASS`/`FAIL` status per scenario between
  runs.
- Only compare runs with matching `suite_hash`; if the hash changed, the suite
  changed and the comparison isn't apples-to-apples.

See [Results](/cqf-bench/concepts/results/) and
[Output Format](/cqf-bench/reference/output-format/) for the fields to diff.
