# Concrete patches for Codex (unified suite + naked retrieve + full review)

Use each block below as a separate task/prompt for Codex. Order matters: do Patches 1–5 first (unified suite + Q203-RR), then 6–11 (selectivity, warmup, report metadata, throughput, data generator, scale matrix).

---

## Patch 1: Add payload template for “retrieve with non-indexed filter” (clinicalStatus)

**Description for Codex:**

In `scripts/run_benchmark.py`, add a new payload template named `resident_bundle_transaction_with_clinical_status` used by a scenario that forces a non-indexed retrieve (filter by something other than code or date).

- In `make_payload()`, when `template_name == "resident_bundle_transaction_with_clinical_status"`, build a FHIR Bundle (type transaction) with:
  - One Patient (id = `patient_id`).
  - Multiple Condition resources for that patient: some with `"clinicalStatus": { "coding": [{ "system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active" }] }` (matching) and the rest with `"code": "inactive"` in the same system (non-matching). Use a fixed mix so that roughly 20% of conditions are active and 80% inactive (e.g. 8 active, 32 inactive, or similar) so engines must do a full scan and filter on clinicalStatus rather than code or date indexes.
  - Each Condition must have `id`, `subject` (reference to the patient), and `code` (any single Snomed code, e.g. 38341003) so the only discriminating filter in the upcoming CQL is clinicalStatus.
- Reuse the same structure as `resident_bundle_transaction_with_dates` (entries list with request/resource) so the runner can POST it as setup.

No new scenario yet; this patch only adds the payload template.

---

## Patch 2: Add scenario Q203-RR “Retrieve with non-indexed filter (clinicalStatus)”

**Description for Codex:**

In `bench/scenarios/tpcqf_v2.json`, add a new scenario object to the `scenarios` array, placed **after** Q202-RR and **before** Q301-RR:

- **id:** `Q203-RR`
- **name:** `Retrieve with non-indexed filter (clinicalStatus)`
- **kind:** `compute`
- **method:** `GET`
- **path:** `/$cql`
- **query:** `"expression": "exists([Condition] C where C.clinicalStatus = 'active')"`, `"subject": "Patient/{patient_id}"`
- **required_capabilities:** `["system_cql", "resident_execute", "resident_data_load"]`
- **expected_status:** `[200, 400, 422]`
- **setup:** method POST, path_role `data`, path `/Bundle`, `payload_template`: `resident_bundle_transaction_with_clinical_status`, per_patient true, expected_status [200, 201].

If the CQL engine expects clinicalStatus as a code from a coding (e.g. `C.clinicalStatus.coding[0].code = 'active'`), use the expression that filters on clinicalStatus only, not on code or date. This scenario forces non-indexed evaluation (filter on clinicalStatus).

---

## Patch 3: Create unified TPCQF suite (single file, no v1/v2)

**Description for Codex:**

1. Create `bench/scenarios/tpcqf.json` by copying the full content of `bench/scenarios/tpcqf_v2.json` (which after Patch 2 already includes Q203-RR). Then in that new file only, change:
   - `"suite_id"` from `"TPCQF-v2"` to `"TPCQF"`.
   - `"description"` to: "CQF benchmark suite: operation family and artifact/data mode (single canonical set)."

2. Delete `bench/scenarios/tpcqf_v1.json` and `bench/scenarios/tpcqf_v2.json`.

3. The canonical TPCQF suite is now `bench/scenarios/tpcqf.json` with suite_id `TPCQF`; there are no v1/v2 variants.

---

## Patch 4: Point all defaults and docs to the unified suite

**Description for Codex:**

Update every reference to the old suite files so the project uses the single unified suite only.

1. **scripts/run_benchmark.py**  
   Change the default for `--suite` from `bench/scenarios/tpcqf_v1.json` to `bench/scenarios/tpcqf.json`.

2. **scripts/run_scale_matrix.sh**  
   Change the default for `SUITE_FILE` from `bench/scenarios/tpcqf_v1.json` to `bench/scenarios/tpcqf.json`.

3. **README.md**  
   - In the “Layout” (or “Scenario set”) section, remove references to `tpcqf_v1.json` and `tpcqf_v2.json`. Describe a single suite: `bench/scenarios/tpcqf.json` with suite_id TPCQF, and list its scenarios (including Q203-RR).
   - Replace any `--suite bench/scenarios/tpcqf_v2.json` or `tpcqf_v1.json` in examples with `--suite bench/scenarios/tpcqf.json`.
   - Remove the “Scenario set (TPCQF-v1, legacy IDs)” section and any v1/v2 comparison; keep one “Scenario set (TPCQF)” with the current scenario IDs (Q001-RR, Q101-RR, … Q203-RR, … Q304-RR).

4. **BENCHMARK_TESTS.md**  
   - Remove the “Suite: TPCQF-v1” section and the “Suite: TPCQF-v2” section.
   - Add a single “Suite: TPCQF” section that documents the scenario file as `bench/scenarios/tpcqf.json` and describes every scenario (including Q203-RR: “Retrieve with non-indexed filter (clinicalStatus)” — system $cql with resident data; CQL filters on Condition.clinicalStatus so engines cannot rely on code or date indexes).
   - Remove the “Mapping from v1 IDs” paragraph (no longer needed).

---

## Patch 5: Document Q203-RR and “naked retrieve” in BENCHMARK_TESTS

**Description for Codex:**

In `BENCHMARK_TESTS.md`, in the TPCQF suite section, add or complete the entry for Q203-RR:

- **Q203-RR Retrieve with non-indexed filter (clinicalStatus)**  
  - Endpoint: GET `/$cql` with query params expression and subject.  
  - Class: compute.  
  - CQL: `exists([Condition] C where C.clinicalStatus = 'active')`.  
  - Setup: POST Bundle with payload_template `resident_bundle_transaction_with_clinical_status` (per patient).  
  - Purpose: Force a retrieve that cannot be satisfied by code or date indexes; filter is on clinicalStatus so implementations must use a non-indexed (full-scan or predicate) approach.

Ensure no remaining references to TPCQF-v1 or TPCQF-v2 in this file.

---

## Patch 6: Configurable selectivity in benchmark runner (default 20%)

**Description for Codex:**

Make match vs non-match ratio configurable so users can stress engines (e.g. default 20% match, 80% non-match).

1. **CLI and suite:**  
   - In `scripts/run_benchmark.py`, add `--selectivity` argument (type float, default `0.2`, help e.g. "Target fraction of matching rows in selectivity-sensitive payloads (0.0–1.0). Default 20%.").  
   - When building the run, resolve selectivity per scenario: use `scenario.get("selectivity")` if present, else `suite.get("defaults", {}).get("selectivity")`, else `args.selectivity`. Pass this resolved value into payload construction for that scenario.

2. **make_payload signature and call sites:**  
   - Change `make_payload(template_name: str, patient_id: str)` to `make_payload(template_name: str, patient_id: str, selectivity: float = 0.2)`.  
   - Every caller that uses a payload template (e.g. `prepare_payload` for setup and main) must pass the resolved selectivity for that scenario. So `prepare_payload` (and any direct `make_payload` call) needs access to the scenario’s resolved selectivity; the runner should resolve selectivity once per scenario and pass it when calling `prepare_payload` / into the code path that calls `make_payload`.

3. **Templates that use selectivity:**  
   - In `resident_bundle_transaction_with_dates`: instead of hardcoded `matching_count = 3` and `non_matching_count = 40`, use a fixed total (e.g. 43) and set `matching_count = max(0, round(43 * selectivity))`, `non_matching_count = 43 - matching_count` (or similar so total is stable).  
   - In `resident_bundle_transaction_with_clinical_status`: same idea — use a fixed total number of conditions and set the number of “active” (matching) vs “inactive” (non-matching) from `selectivity`.

4. **Documentation:**  
   - In `BENCHMARK_TESTS.md`, add a short “Selectivity” subsection under the measurement model: scenarios that use payload templates with match/non-match mix (e.g. Q202-RR, Q203-RR) respect the suite default or per-scenario `selectivity` (and CLI `--selectivity`); default is 0.2 (20% match). This allows users to stress systems with different ratios.

---

## Patch 7: Warmup before measured phase

**Description for Codex:**

Implement warmup so reported latency is not inflated by cold caches or JIT.

1. **Use suite default:**  
   - In `scripts/run_benchmark.py`, read `warmup_requests` from the suite’s `defaults` (e.g. `defaults.get("warmup_requests", 0)`). If 0, skip warmup.

2. **Run warmup in run_scenario:**  
   - Before the main measured phase (the existing ThreadPoolExecutor loop that records latencies), run a warmup phase: issue the same requests as the main phase (same method, URL, payload per patient) for the first N requests only, where N = min(warmup_requests, len(patient_ids)). Do not record latency or pass/fail for these requests. Then run the full main phase as today and record all latencies and status counts as now.

3. **No warmup for setup:**  
   - Warmup applies only to the main phase of each scenario, not to setup.

4. **Docs:**  
   - In `BENCHMARK_TESTS.md`, under “Measurement model” or “Reproducibility”, state that the runner may run up to `warmup_requests` (from suite defaults) main-phase requests before the measured main phase; those are not included in latency or pass_rate.

---

## Patch 8: Report metadata for reproducibility

**Description for Codex:**

Include config and version in the report so runs are reproducible.

1. **In `scripts/run_benchmark.py`,** when building the `report` dict (before writing JSON), add:
   - `suite_file`: string path of the suite file (e.g. `str(args.suite)` or resolved path).
   - `engines_file`: string path of the engines config file (e.g. `str(args.engines)`).
   - `git_commit`: optional string. If the current working directory is inside a git repository, set it to the output of `git rev-parse HEAD` (strip whitespace). If not in a repo or command fails, omit the key or set to `null`.

2. **Documentation:**  
   - In README “Notes on comparability” (or “Reports”), mention that each report includes `suite_file`, `engines_file`, and when available `git_commit` for reproducibility.

---

## Patch 9: Throughput in report and summarizer

**Description for Codex:**

Add throughput (requests per second) so users can compare engines on both latency and throughput.

1. **In `scripts/run_benchmark.py`:**  
   - In `run_scenario`, record wall-clock time for the main phase only: start a timer immediately before submitting tasks to the executor and stop it when all futures have completed. Compute `requests_per_second = total_requests / elapsed_seconds` (elapsed_seconds from that timer). Add `requests_per_second` (float) to the result dict for each scenario. If `elapsed_seconds` is 0, set `requests_per_second` to 0 or omit.

2. **Report output:**  
   - Ensure the per-scenario result in the JSON report includes `requests_per_second`. In `write_markdown_summary`, add a column or line for throughput (e.g. “req/s”) next to p95/p99 in the table.

3. **summarize_report.py:**  
   - When printing per-scenario results, also print `requests_per_second` (e.g. “req/s=12.3”) if present in the report.

---

## Patch 10: Selectivity and scale in synthetic data generator

**Description for Codex:**

Align the data generator with benchmark concepts (scale, selectivity) and document how it relates to the benchmark.

1. **Arguments in `scripts/generate_synthetic_data.py`:**  
   - Add `--selectivity` (type float, default `0.2`, help e.g. "Fraction of observations (or resources) that are 'matching' for stress-testing; 0.0–1.0.").  
   - Add optional `--scale` as an alias or alternative to `--patients` (e.g. `--scale` sets the same count as `--patients` for consistency with benchmark `--scale`). Either: add `--scale` that sets the same number as `--patients` (if both given, prefer one or error), or document that `--patients` corresponds to benchmark scale.

2. **Use selectivity in generated data:**  
   - For observations (or a second resource type that has a “match” vs “non-match” dimension): generate a mix so that roughly `selectivity * N` rows are “matching” and the rest “non-matching”. For example: add a boolean or code field that distinguishes match vs non-match (e.g. different observation codes or value ranges), and choose it according to selectivity so that approximately that fraction of rows are matching. Keep output as NDJSON (patients.ndjson, observations.ndjson).

3. **Documentation:**  
   - In the script docstring or README “Optional synthetic data generation” section, state that: `--patients` (or `--scale`) is the number of patients and aligns with benchmark `--scale`; `--selectivity` controls the match/non-match ratio in the generated data (default 20%) for alignment with benchmark selectivity when this data is used for load/ETL or future file-based payloads.

---

## Patch 11: run_scale_matrix.sh use strict-2xx and optional suite/env

**Description for Codex:**

Make scale sweeps suitable for performance comparison by default.

1. **In `scripts/run_scale_matrix.sh`:**  
   - Add `--score-mode strict-2xx` to the `run_benchmark.py` invocation so that scale matrix runs use strict 2xx scoring (recommended for performance comparison).  
   - Keep `SUITE_FILE` and `ENGINES_FILE` as env overrides; default `SUITE_FILE` should already point to `bench/scenarios/tpcqf.json` after Patch 4.

2. **README:**  
   - In “Run scale sweep”, mention that the script uses `--score-mode strict-2xx` by default so results are comparable; users can override by modifying the script or running `run_benchmark.py` manually with different options.

---

## Patch 12 (optional): Remove or implement requests_per_patient

**Description for Codex:**

The suite JSON files have `defaults.requests_per_patient` (e.g. 1) but the runner does not use it. Choose one:

- **Option A (remove):** Remove `requests_per_patient` from all `defaults` in `bench/scenarios/*.json` and from any documentation that mentions it, so the schema does not imply behavior that isn’t implemented.  
- **Option B (implement):** In `run_scenario`, read `requests_per_patient` from scenario or suite defaults (default 1). For each patient, issue that many main-phase requests (same URL/payload), and count all in total_requests / latencies / pass rate. So total requests = len(patient_ids) * requests_per_patient.

Implement either Option A or B; document the choice briefly in BENCHMARK_TESTS.md.

---

## Summary

| Patch | What |
|-------|------|
| 1 | Add `resident_bundle_transaction_with_clinical_status` payload template in `run_benchmark.py` |
| 2 | Add scenario Q203-RR to tpcqf_v2.json |
| 3 | Create `tpcqf.json` (unified), delete `tpcqf_v1.json` and `tpcqf_v2.json` |
| 4 | Defaults and docs: runner, run_scale_matrix.sh, README, BENCHMARK_TESTS → single suite only |
| 5 | Document Q203-RR and “naked retrieve” in BENCHMARK_TESTS.md |
| 6 | Configurable selectivity (CLI, suite, make_payload, Q202-RR/Q203-RR templates); document in BENCHMARK_TESTS |
| 7 | Implement warmup (suite default warmup_requests, run before main phase, do not record); document |
| 8 | Report metadata: suite_file, engines_file, git_commit; document in README |
| 9 | Throughput: requests_per_second per scenario in report, markdown summary, and summarize_report.py |
| 10 | Data generator: --selectivity (default 0.2), use in generated mix; document scale/selectivity vs benchmark |
| 11 | run_scale_matrix.sh: add --score-mode strict-2xx; document in README |
| 12 | Optional: remove requests_per_patient from suite defaults and docs, or implement it in run_scenario |

**Order:** 1 → 2 → 3 → 4 → 5 (unified suite + Q203-RR), then 6 → 7 → 8 → 9 → 10 → 11 → 12.
