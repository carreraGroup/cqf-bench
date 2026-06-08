# Synthetic dataset layout (`--generated-data-root`)

After **generate**, a payload directory is a single reusable **dataset**: one
synthetic patient cohort and payloads for every scenario in the built-in
benchmark suite (`bench/scenarios/tpcqf/suite.yaml`). There is no per-run suite
path for generate—the harness always uses that definition.

## Words: suite, scenario, `setup`, `main`

**Suite** — The whole benchmark definition: `suite.yaml` plus one folder per
`scenario_id`. **Generate** reads this fixed tree so it knows each scenario’s
`data.yaml`, mutators, HTTP paths, and CQL. **Load** / **execute** can still take
an optional `--suite` override for advanced use; otherwise they use
`suite_file` from `dataset.json` (legacy trees) or the same default suite path.

**Scenario** — One benchmark case (one row in the report), e.g. `CAP001-P`
(preload) or `CAP001-I` (inline).

**`setup` and `main` (phases)** — Two *kinds* of FHIR payload the harness may
need:

| Phase | Meaning | Typical use |
| --- | --- | --- |
| **Resident (`setup` in YAML)** | Bundles you **POST into the server** so facts **live in the datastore** before timed `$evaluate`. | Preload **`-P`** scenarios. |
| **`main`** | Payloads for the **timed HTTP call** (e.g. `Parameters` with an inline bundle). | **`-I`** scenarios. |

## Current layout: `unified-corpus-v3` (new generate output)

Generate writes **one merged resident corpus** plus **compiled per-scenario inline**
payloads:

| Path | Purpose |
| --- | --- |
| `dataset.json` | Manifest: `layout`, `suite_id`, `scale`, `selectivity`, paths description. **load** / **execute** read `scale` (and legacy `suite_file`) when CLI args are omitted. |
| `corpus/starter/p1.json` | Starter-equivalent resident bundle at scale 1 / suite-default selectivity, emitted so the shared corpus baseline is explicit rather than implicit in generator code. |
| `corpus/setup/<patient_id>.json` | **Single** merged transaction `Bundle` per patient: all resident setup resources from every scenario that defines `setup:`, deduped by `(resourceType, id)`. **Load** POSTs this **once per patient** (not once per scenario). |
| `corpus/preload/<scenario_id>/setup/<patient_id>.json` | Scenario-specific resident setup bundles retained for preload correctness. Current **load** prefers these per-scenario bundles because some preload scenarios are not yet mutually compatible in one shared resident pool. |
| `corpus/inline/<scenario_id>/<patient_id>.json` | Inline payloads for **execute**, compiled during **generate** from explicit assembly specs against the generated resident corpus. |
| `corpus_coverage.json` | Coverage/validation manifest emitted at generate time; generation fails if required inline resource keys are missing from the merged resident corpus. |

Detection: if `corpus/setup/` is a directory, the harness treats the tree as
unified.

## Legacy layout (older trees, tests, existing fixtures)

| Path | Purpose |
| --- | --- |
| `dataset.json` | Includes `suite_file` pointing at the suite used when the tree was generated. |
| `<scenario_id>/setup/<patient_id>.json` | Resident bundles POSTed during **load** (one scenario at a time). |
| `<scenario_id>/main/<patient_id>.json` | Inline payloads for **execute**. |

**Load** walks every scenario’s `setup/` directory. **Execute** still strips YAML
`setup` and uses disk `main/` when overrides are applied.

## Reuse

- **Generate once** at a given `scale` and `selectivity` (fixed suite).
- **Load once** per engine: unified trees do **one** merged preload pass; legacy
  trees do one setup pass per scenario that has `setup:`.
- **Execute** many times; use `--scenario` (repeatable) on `run_benchmark.py` to
  run a subset, or omit it to run the full suite. Mixed runs execute
  conformance probes first, then resident/preload scenarios, then inline scenarios.

All scenarios are included in every generate run. The **resident** clinical
namespace is shared: merged setup is one corpus for the whole suite.

## User workflow

1. **Generate** — builds the resident corpus and compiles inline request bodies.
2. **Load** — optional; required only if the next run includes preload/resident scenarios. Current implementation loads the generated per-scenario preload bundles in this step.
3. **Execute** — runs the selected scenarios and writes the report as part of the same step.

Inline runs should use the compiled artifacts from `corpus/inline/`; execute does
not discover bundle contents from the live server.

## Operational note

Scenarios that run destructive cleanup before setup can still evict data from
other scenarios on the same server. For maximum reuse of **resident** data,
prefer additive, idempotent bundles and suite rules that do not cross-delete.
