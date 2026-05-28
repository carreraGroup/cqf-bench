---
title: Results
description: What a benchmark run produces, how outcomes are scored, and how to read the matrices.
---

Every run writes two artifacts to the output directory (default `results/`):

- `results/<run_id>.json` — the complete machine-readable report.
- `results/<run_id>.md` — a human-readable Markdown summary.

`<run_id>` is `<suite_id>_<scale>_<random_suffix>`, e.g.
`TPCQF_100_ab12cd`. For the precise JSON schema and field-by-field reference, see
[Output Format](/cqf-bench/reference/output-format/).

## Provenance

Each report records enough to reproduce and trust it:

- `suite_id`, `suite_file`, and a `suite_hash` over all scenario files,
- the `git_commit` of the harness,
- `scale`, `concurrency`, `timeout_seconds`, `score_mode`, `repetitions`,
- start/end timestamps (UTC and local) and `duration_seconds`.

Because the suite hash and git commit are captured, two reports can be compared
meaningfully — you know whether a difference came from the engine or from a change
to the suite.

## How outcomes are scored

### Conformance scenarios

Scored purely by HTTP class against the scenario's `expected_http` policy:

- `PASS` — status in `success` (2xx).
- `UNSUPPORTED` — status in `unsupported` (e.g. 422).
- `WARNING` — status in `warning` (other 4xx).
- `FAIL` — status in `fail`, any unclassified status, 5xx, or timeout.

Conformance rows are never timed.

### Capability scenarios

A capability scenario row is `PASS` only when **all** of the following hold:

- no failed requests,
- no unsupported requests,
- no warning requests,
- no timed-out requests,
- at least one timed, correct request,
- no non-200 status codes were observed.

Otherwise the row is `FAIL`, annotated with the reason (incorrect result,
unsupported, warning, timeout, and the observed HTTP status). **Timing is shown
only for PASS rows**, so a fast-but-wrong response never earns a latency number.

## Timing metrics

For PASS capability rows, the report records latency in milliseconds:

| Metric | Meaning |
| --- | --- |
| `min`, `avg`, `max` | Across timed requests. |
| `p50`, `p95`, `p99` | Latency percentiles across timed requests. |
| `avg_p95_over_repetitions` | The p95 averaged across repeated runs (`--repetitions` / `--runs`). |

The Markdown matrix shows `avg_p95_over_repetitions` (falling back to `p95`) as
the headline time. Requests-per-second and average-over-all-latencies are also
recorded in JSON.

## Reading the Markdown report

The Markdown summary opens with the run header, then presents up to two matrices.

### Conformance Matrix

One row per `CONF###` scenario; for each engine, three columns —
**Result** (`PASS`/`FAIL`), **Time** (blank, since conformance is untimed), and
**Note** (`unsupported` / `warning`, the endpoint used, and the observed HTTP
status).

```markdown
## Conformance Matrix

| Scenario | Intent | hapi-cqf-ruler-local Result | hapi-cqf-ruler-local Time | hapi-cqf-ruler-local Note |
|---|---|---|---|---|
| CONF010 | GET /Library/$evaluate conformance | PASS |  | endpoint: GET /Library/$evaluate; HTTP 200 |
| CONF030 | POST /Measure/$care-gaps conformance | FAIL |  | unsupported; HTTP 422 |
```

### Capability + Performance Matrix

One row per `CAP###` scenario; for each engine, **Result**, **Time** (only on
PASS), and **Note** (failure reason, unsupported/warning/timeout counts, endpoint,
HTTP status).

```markdown
## Capability + Performance Matrix

| Scenario | Intent | hapi-cqf-ruler-local Result | hapi-cqf-ruler-local Time | hapi-cqf-ruler-local Note |
|---|---|---|---|---|
| CAP001-P | Count retrieve all of one resource (preload) | PASS | 47.0ms |  |
| CAP006-I | Retrieve with with-clause join (inline) | FAIL |  | incorrect result; HTTP 200 |
```

When multiple engines are selected, each engine adds its own
`Result` / `Time` / `Note` column group, so engines sit side by side for direct
comparison. See [Compare Engines](/cqf-bench/guides/compare-engines/).

## Quick terminal summary

For a fast textual digest of a JSON report:

```bash
python scripts/summarize_report.py results/<run_id>.json
```

This prints per-engine, per-scenario lines with timed/unsupported/fail counts and
p95/p99 where available.
