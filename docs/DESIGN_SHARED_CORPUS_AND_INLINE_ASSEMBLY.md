# Design: Shared corpus, phased execution, and compiled inline payloads

**Status:** Proposal (implementation-ready spec)  
**Audience:** Implementer (e.g. Codex) — no prior chat context required  
**Scope:** TPCQF-style bench (`bench/scenarios/tpcqf`); harness (`scripts/run_benchmark.py`) and generate/load/execute flow

---

## 1. Goals

1. **One clinical substrate** — A single, carefully designed starter corpus (baseline scale and selectivity) that is **permuted/scaled** mechanically (more patients, repeated patterns, date shifts, counts). The large pool does **not** encode per-scenario semantics beyond **field variation** needed for predicates (codes, statuses, dates, links, edge cases).

2. **No per-scenario resident POST in the timed path** — Resident data is **generated once** and **loaded once** (optional step). Scenario execution assumes the server already holds the pool (for preload-style scenarios).

3. **Scenario semantics = ValueSets + CQL predicates + validators** — Scenarios slice the pool using **terminology** (ValueSets) **and** non-code **predicates** (status, dates, joins, null-id edges, etc.). The corpus must **contain witnesses** for those predicates; scenarios do not each mint a disjoint world.

4. **Inline bodies are compiled, not inferred** — For `-I` (inline) scenarios, the HTTP body is a **deterministic artifact** produced at **generate** time, keyed by `(scenario_id, patient_id, selectivity)` (and suite revision). **Execute** must not assemble bundles by scanning the corpus at runtime.

5. **Phased execution for operators** — Clear user steps:
   - **Generate** data (always, or when inputs change).
   - **Load** (optional) — only required if the user will run **resident/preload** scenarios.
   - **Run** — subset or full suite; execution may run **resident-capable scenarios first**, then **inline** scenarios (or explicit flags).

---

## 2. Non-goals (for this phase)

- Replacing FHIR/CQL semantics or engine adapters.
- Auto-discovering inline bundle contents by evaluating CQL against the server at execute time.
- Solving multi-tenant isolation on a shared server beyond idempotent additive loads (document assumptions).

---

## 3. Core concepts

### 3.1 Starter corpus

- **Definition:** `scale = 1` (or defined “unit scale”) and a **baseline selectivity** (suite default, e.g. 0.2) produce the **starter** resource set: minimal patients and a **rich** set of Conditions, Observations, and supporting resources.
- **Requirements:** Every **predicate family** the suite uses must have at least one **witness** (and usually match vs non-match counts where selectivity applies). Predicate families include:
  - ValueSet / code membership
  - `clinicalStatus`, `verificationStatus`, Observation `status`
  - temporal fields (`recordedDate`, `effective`, etc.)
  - subject linkage, semi-join patterns (e.g. Observation only on subset of Conditions)
  - structural edges (e.g. missing `id`, specific cardinality)
- **Permutation:** Scaling to `N` patients and other selectivities is **mechanical**: duplicate/rewrite anchors (`patient_id`), re-seed counters, multiply rows, shift dates — **without** embedding scenario ids into resources unless using an explicit **tag/slot** scheme (see 3.3).

### 3.2 Shared pool vs scenario “lens”

- The **pool** is dumb data with wide variation.
- Each scenario defines a **lens**: CQL + optional ValueSets + **predicates** on non-code fields. The **generator** (or a validator step) must prove the pool **satisfies** each scenario’s lens at declared selectivity, or generation fails.

### 3.3 Optional: slot / cohort tagging

To keep assembly specs short and permutation-safe, generated resources MAY use:

- deterministic **id patterns** (`{slot}-{patient_id}-…`), and/or  
- **`meta.tag`** / extension **cohort keys** (e.g. `bench:slot:cond-match`, `bench:family:semi-join`).

This is **not** “the corpus tells you the HTTP body”; it is **indexing** so the **assembly spec** can reference stable slots after permutation.

---

## 4. Inline payload assembly (mandatory design)

### 4.1 Principle

**Inline request bodies are compiled artifacts.**  
The system knows what to send because **generation** ran an **assembler** that consumed:

1. **Assembly specification** for the scenario (or scenario family + delta), and  
2. **Materialized corpus** for `(patient_id, selectivity)` (and scale),

and wrote **exactly one JSON (or equivalent) file per key**.

### 4.2 Assembly specification (per scenario or family)

Current implementation is **assembly v1**: explicit YAML `assembly.yaml` beside
each inline `scenario.yaml`.

- **v1 source:** `paired_preload_setup`
- **v1 behavior:** generation builds the paired `CAP###-P` setup bundle for the
  same patient/selectivity, then filters the merged resident corpus by the
  resulting `(resourceType, id)` keys.
- **v1 transforms:** `output_mode` controls the final request shape
  (`parameters_data` today).

This keeps execute-time behavior deterministic while acknowledging that the
current YAML is still minimal and the richer “inclusion rule” language remains a
future extension.

**Forbidden:** execute-time “find resources that satisfy this CQL” against the live server as the only selection mechanism.

### 4.3 Output keys

Compiled inline payloads MUST be addressable as:

`corpus/inline/<scenario_id>/<patient_id>.json`  
(or include `selectivity` in path/filename if multiple selectivities are generated from one tree, e.g. `.../sel020/p1.json`).

Execute phase MUST load these files the same way it today loads `main/` — no new runtime logic beyond path resolution.

### 4.4 Family templates (optional optimization)

Where many `-I` scenarios share the same bundle shape, define:

- **Family template** + **per-scenario delta** (extra ValueSet, small resource set, parameter shape).

Compiler expands to the same per-key output files.

---

## 5. Operator workflow (product contract)

| Step | Action | When optional |
|------|--------|-----------------|
| 1 | **Generate** — starter + permutation + compile all inline payloads + manifests | Never skip if data or suite changed |
| 2 | **Load** — PUT/POST merged resident bundle(s) + any existing artifact preloads (libraries, measures, ValueSets) | **Optional** if the user runs **inline-only** scenarios |
| 3 | **Execute** — run chosen scenarios | Always |

**Execute ordering (default):** run scenarios that require **resident data** (or assume it) **before** scenarios that are **inline-only**, when both are selected in one invocation. Allow override flags for power users.

**Capabilities:** engines without `resident_data_load` skip load and resident scenarios; engines without `inline_bundle_execute` skip inline scenarios — behavior should remain explicit in reports (skipped + reason).

---

## 6. Artifacts and manifests (implementation checklist)

Implementers SHOULD define or extend:

| Artifact | Purpose |
|----------|---------|
| `dataset.json` (or successor) | `scale`, `selectivity`, `layout` version, suite id/revision hash, paths to corpus roots |
| Starter corpus directory | Scale-1 baseline (or documented “unit”) |
| Permuted corpus | `Patient`… resources for `p1..pN` consistent with permutation rules |
| `corpus/resident/` (name TBD) | One or few **merged transaction bundles** per patient for **single** load POST (if still one POST per patient) |
| `corpus/inline/...` | Compiled inline bodies per key (§4.3) |
| `assembly.yaml` (or equivalent) | Per-scenario (or family) spec consumed only at generate |
| Coverage manifest (optional) | Matrix: scenario × predicate dimensions × min counts — used to validate starter + permutation |

---

## 7. Relationship to current codebase (handoff hints)

- Today: `run_benchmark.py` has generate/load/execute phases, adapters, `prepare_payload`, FSH mutation pipeline, legacy `<scenario>/setup|main/` trees, and newer unified `corpus/setup` + `corpus/main` layout.
- **Target:** resident load uses **one** merged resident bundle per patient from the **shared permuted pool**; **no** per-scenario resident setup in execute.
- **Target:** inline uses **`corpus/inline/...`** compiled from **assembly specs**, not only `data.yaml` `main` generator unless that pipeline is refactored to be the assembler backend.

Implementer should grep for: `prepare_payload`, `fsh_mutation`, `output_mode`, `apply_generated_*_overrides`, `load_unified_corpus_preload`, `run_scenario`.

---

## 8. Acceptance criteria (definition of done)

1. **Generate** at baseline produces a **validated** starter; **permute** to `scale=N` produces consistent anchors and no id collisions across patients.
2. **Every** inline scenario has a **compiled** body on disk for each `(patient_id, selectivity)` the suite claims to support; missing file = **generate failure**, not silent execute failure.
3. **Load** is skippable for an inline-only run and documented in CLI help.
4. **Execute** with mixed selection runs resident-assuming scenarios after load when load occurred; skips with clear reason when capabilities or artifacts missing.
5. **No** execute-time bundle assembly from an unindexed corpus without an assembly spec (reviewer checklist item).

---

## 9. Suggested implementation order

1. Schema for **assembly spec** + minimal compiler → emit `corpus/inline/...` for one pilot `-I` scenario.  
2. **Starter corpus** module + permutation + validation hooks.  
3. **Single resident merge** per patient from pool (replace per-scenario setup merge logic).  
4. Wire **load optional** + **execute phase ordering** + docs/CLI.  
5. Migrate remaining scenarios in batches (family templates to reduce spec duplication).

---

## 10. Implementation decisions

- [x] Exact **assembly spec** format — per-inline-scenario YAML file at
  `bench/scenarios/tpcqf/<scenario_id>/assembly.yaml`, currently schema `version: 1`.
- [x] **ValueSet** resources — keep following repo conventions and permit them in
  the generated resident bundles when the paired preload fixtures include them.
- [x] **Selectivity** layout — one selectivity per generated tree; `dataset.json`
  records the active `selectivity`.
- [x] **CONF** scenarios — stay in the same execute binary; default ordering is
  conformance probes first, then resident/preload scenarios, then inline scenarios.
- [x] **Preload correctness fallback** — generated trees also retain
  scenario-specific resident setup bundles under `corpus/preload/...`; current
  load prefers those bundles because some preload scenarios remain incompatible
  inside one shared resident pool until the starter corpus is redesigned.

---

*End of design doc — suitable for handoff without external context.*
