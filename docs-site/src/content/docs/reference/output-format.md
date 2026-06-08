---
title: Output Format
description: The JSON report schema and Markdown summary produced by a benchmark run.
---

Each run writes the core report pair plus a comparison bundle to the output directory (default `results/`):

- `results/<run_id>.json` — the complete machine-readable report.
- `results/<run_id>.md` — a human-readable Markdown summary.
- `results/<run_id>.summary.json` — aggregated per-engine counts and PASS latency comparisons.
- `results/<run_id>.summary.md` — a concise comparison summary for sharing.
- `results/<run_id>.conformance-status.svg` — stacked conformance outcome counts by engine.
- `results/<run_id>.capability-status.svg` — stacked capability outcome counts by engine.
- `results/<run_id>.capability-p95.svg` — PASS-only p95 comparison across engines/scenarios.
- `results/<run_id>.report.html` — a branded, self-contained HTML report (see [HTML report](#html-report)).

`<run_id>` is `<suite_id>_<scale>_<random_suffix>`.

## JSON report

### Top-level fields

```jsonc
{
  "run_id": "TPCQF_100_ab12cd",
  "suite_id": "TPCQF",
  "suite_file": "bench/scenarios/tpcqf/suite.yaml",
  "suite_hash": "…",                       // sha256 over all scenario files
  "scenario_files_hashed": ["…"],          // files included in suite_hash
  "engines_file": "bench/config/local.engines.yaml",
  "git_commit": "…",                        // harness commit, or null
  "scale": 100,
  "concurrency": 16,
  "timeout_seconds": 30,
  "score_mode": "compat",                   // compat | strict-2xx
  "repetitions": 1,
  "run_phase": "execute",                   // execute (reports); generate/load omit this artifact
  "generated_data_root": null,              // path; directory may include dataset.json for load/execute defaults
  "started_epoch": 1700000000.0,
  "started_utc": "2026-01-01T00:00:00+00:00",
  "started_local": "…",
  "ended_epoch": 1700000000.4,
  "ended_utc": "…",
  "ended_local": "…",
  "duration_seconds": 0.43,
  "engines": [ /* per-engine objects */ ]
}
```

### Per-engine object

```jsonc
{
  "name": "hapi-cqf-ruler-local",
  "base_url": "http://localhost:8081",
  "cqf_base_path": "/fhir",
  "results": [ /* per-scenario result objects */ ]
}
```

### Per-scenario result object

```jsonc
{
  "scenario_id": "CAP001-P",
  "scenario_name": "Count retrieve all of one resource (preload)",
  "kind": "compute",
  "test_type": "capability",                 // capability | conformance
  "required_capabilities": ["resident_data_load", "resident_execute"],
  "setup": { /* setup phase result, or null */ },

  "total_requests": 100,
  "pass_requests": 100,
  "pass_rate": 1.0,
  "failure_rate": 0.0,

  "http_pass_requests": 100,
  "correct_pass_requests": 100,
  "correct_pass_rate": 1.0,
  "validate_eligible_requests": 100,

  "timed_requests": 100,
  "timed_ok_requests": 100,
  "unsupported_requests": 0,
  "warning_requests": 0,
  "timeout_requests": 0,
  "fail_requests": 0,

  "status_counts": { "200": 100 },

  "latency_ms": {
    "min": 31.2,
    "avg": 44.9,
    "p50": 43.0,
    "p95": 47.0,
    "p99": 51.5,
    "max": 60.1,
    "avg_p95_over_repetitions": 47.0
  },
  "requests_per_second": 22.1,
  "all_latency_ms_avg": 44.9,

  "endpoint_used": { /* effective method/path actually called */ },
  "incorrect_result_failures": 0,
  "incorrect_result_notes": []
}
```

Conformance results additionally carry `conformance_status`
(`PASS` / `UNSUPPORTED` / `WARNING` / `FAIL`) and `conformance_note`.

### Field notes

| Field | Meaning |
| --- | --- |
| `pass_rate` | `timed_ok_requests / total_requests`. |
| `http_pass_requests` | Requests whose HTTP status was a success. |
| `correct_pass_requests` | Requests that passed both HTTP and correctness validators. |
| `correct_pass_rate` | `correct_pass_requests / validate_eligible_requests`. |
| `timed_requests` / `timed_ok_requests` | Requests that contributed to latency (PASS only). |
| `unsupported` / `warning` / `timeout` / `fail` _requests_ | Counts per outcome bucket. |
| `status_counts` | Map of HTTP status code → count observed. |
| `latency_ms` | Latency stats over timed (PASS) requests; `null` if none. |
| `avg_p95_over_repetitions` | p95 averaged across repeated runs; the headline time in the Markdown matrix. |
| `endpoint_used` | The effective method/path the adapter actually called (and which CONF it derived from, if dynamic). |
| `incorrect_result_notes` | Up to five human-readable correctness failure reasons. |

:::caution
Older reports in `results/` may predate the current schema (for example, using
`Q01`-style scenario IDs and a single per-engine table). The schema above
reflects the current `run_benchmark.py` output.
:::

## Markdown summary

The Markdown file opens with a run header:

```markdown
# CQF Benchmark Report: TPCQF_100_ab12cd

- suite: `TPCQF`
- scale: `100`
- concurrency: `16`
- started_utc: `…`
- started_local: `…`
- ended_utc: `…`
- ended_local: `…`
- duration_seconds: `0.43`
- score_mode: `compat`
- repetitions: `1`
```

It then renders up to two matrices.

### Conformance Matrix

One row per `CONF###` scenario. For each engine: **Result** (`PASS`/`FAIL`),
**Time** (always blank — conformance is untimed), and **Note** (`unsupported` /
`warning`, the endpoint used, and the observed HTTP status).

```markdown
## Conformance Matrix

| Scenario | Intent | <engine> Result | <engine> Time | <engine> Note |
|---|---|---|---|---|
| CONF010 | GET /Library/$evaluate conformance | PASS |  | endpoint: GET /Library/$evaluate; HTTP 200 |
```

### Capability + Performance Matrix

One row per `CAP###` scenario. For each engine: **Result**, **Time** (only on
PASS), and **Note** (failure reason, unsupported/warning/timeout counts, endpoint,
HTTP status).

```markdown
## Capability + Performance Matrix

| Scenario | Intent | <engine> Result | <engine> Time | <engine> Note |
|---|---|---|---|---|
| CAP001-P | Count retrieve all of one resource (preload) | PASS | 47.0ms |  |
```

When several engines are selected, each adds its own `Result` / `Time` / `Note`
column group, placing engines side by side.

A row reads `FAIL` with `not executed` when the scenario was skipped for that
engine (missing capability) or excluded by a filter.

## Comparison bundle

The comparison bundle is written alongside the core report files and is derived
from the same JSON report:

- `summary.json` aggregates per-engine conformance/capability outcome counts and
  PASS latency rows.
- `summary.md` turns those aggregates into a compact engine-overview report.
- `*.svg` files provide lightweight comparison charts that can be attached to
  docs, issues, or social posts without additional tooling.
- `report.html` is the branded, shareable HTML report (see [HTML report](#html-report)).

The p95 comparison graph only plots scenarios that produced at least one `PASS`
latency value. Engines/scenarios without a `PASS` result are left blank rather
than plotted with misleading zeros.

When you benchmark engines **sequentially** (one engine per run for fairness),
combine the resulting JSON reports into a single comparison bundle:

```bash
python scripts/compare_reports.py \
  results/run_a.json \
  results/run_b.json \
  --out results/final_compare
```

That writes:

- `results/final_compare.json`
- `results/final_compare.md`
- `results/final_compare.summary.json`
- `results/final_compare.summary.md`
- `results/final_compare.conformance-status.svg`
- `results/final_compare.capability-status.svg`
- `results/final_compare.capability-p95.svg`
- `results/final_compare.report.html`

## HTML report

`<run_id>.report.html` is a single, **self-contained** HTML document — no external
CSS, JavaScript, fonts, or image requests (the logo is embedded). Open it in a
browser, attach it to a PR, email it, or drop it on any static host.

It is generated from the same JSON report and the same aggregates as the Markdown
summary (`build_comparison_summary()` and the canonical `classify_*` helpers), so
its numbers always agree with `summary.md`. The report leads with **speed**, then
**capability pass/fail**, and contains:

- a branded header with run provenance (suite hash, git commit, scale, score mode);
- per-engine **scorecards** (avg PASS p95 headline, then capabilities passed);
- a **correctness-vs-speed quadrant** (top-right = correct *and* fast);
- capability and conformance **outcome bars**;
- a **conformance fingerprint** (checks × engines);
- a **p95-by-scenario line chart** of each engine's latency profile;
- a **latency distribution** (min/p50/p95/p99/max) per scenario;
- the full **capability matrix**.

Read correctness first, speed second — timing is shown only for `PASS` scenarios.

You can also regenerate it from any existing report JSON:

```bash
python scripts/render_html_report.py results/<run_id>.json -o results/<run_id>.report.html
```

## Summarizing a report

```bash
python scripts/summarize_report.py results/<run_id>.json
```

Prints per-engine, per-scenario lines with timed/unsupported/fail counts,
correctness counts, and p95/p99 where available.
