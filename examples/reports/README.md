# Example Reports

These files illustrate what CQF Bench output looks like **without having to run the
harness**. They are **synthetic, illustrative samples** — not the result of a real
benchmark run, and not official results for any engine. Numbers were hand-authored
to demonstrate the report format and status semantics.

Every real run produces a pair of files in `results/`:

- `results/<run_id>.json` — full machine-readable report with reproducibility metadata
- `results/<run_id>.md` — human-readable summary with conformance and capability matrices

## Files here

- [`sample-summary.md`](sample-summary.md) — illustrative Markdown summary (matrix format)
- [`sample-results.json`](sample-results.json) — illustrative JSON report shape
- [`sample-report.html`](sample-report.html) — branded, self-contained HTML report
  (open in a browser). Generated from a real comparison run with
  `scripts/render_html_report.py`; every run also emits a `<run_id>.report.html`.

## How to read a report

Each scenario cell carries a status:

| Status | Meaning |
|---|---|
| `PASS` | Scenario executed and returned the expected result. |
| `FAIL` | Scenario executed but was incorrect, errored, timed out, or returned a warning status. |
| `UNSUPPORTED` | The engine does not support the capability this scenario requires. |
| `NOT_RUN` | Scenario was not executed for this engine (e.g., filtered or skipped). **Not** a correctness failure. |

Key rule: **timing is shown only for `PASS` results.** Performance is never compared
across incorrect, unsupported, or not-run responses. A fast `FAIL` is still a `FAIL`.

See also:

- [Output Format reference](../../docs-site/src/content/docs/reference/output-format.md)
- [GETTING_STARTED.md](../../GETTING_STARTED.md) for how to produce your own report
