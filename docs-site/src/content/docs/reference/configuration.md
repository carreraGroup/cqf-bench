---
title: Configuration Reference
description: Schemas for engines config, suites, scenarios, data, validators, and the mutator.
---

CQF Bench is configured entirely with YAML. This page documents each file type.

## Engines config

The engines config (template: `bench/config/engines.example.yaml`; local:
`bench/config/local.engines.yaml`) lists the servers under test.

```yaml
engines:
  - name: hapi-cqf-ruler-local      # unique engine name (used in --filter-engine and reports)
    adapter: hapi-cqf-ruler         # adapter class: generic-cqf | mercury-cqf | hapi-cqf-ruler | smile-cdr | google-cql
    base_url: http://localhost:8081 # scheme + host + port
    cqf_base_path: /fhir            # base path for CQF operations
    fhir_base_path: /fhir           # base path for FHIR resource writes (libraries, valuesets, …)
    data_base_path: /fhir           # base path for data loading
    headers: {}                     # request headers; values support ${ENV_VAR} expansion
    capabilities:                   # what the engine supports (gates scenario eligibility)
      - resident_data_load
      - resident_execute
      - system_cql
      - inline_bundle_execute
    docker:
      enabled: true                 # whether manage_engines.py controls this engine
      image: alphora/cqf-ruler:latest
      container_name: hapi-cqf-ruler
      host_port: 8081
      container_port: 8080
      env:
        hapi.fhir.cql_enabled: 'true'
      health_path: /fhir/metadata
```

### Engine fields

| Field | Type | Notes |
| --- | --- | --- |
| `name` | string | Unique; referenced by `--filter-engine` and shown in reports. |
| `adapter` | string | Adapter class name; falls back to `generic-cqf` if unknown. |
| `base_url` | string | Scheme, host, and port (no trailing path). |
| `cqf_base_path` | string | Path prefix for CQF operations. |
| `fhir_base_path` | string | Path prefix for FHIR resource writes. |
| `data_base_path` | string | Path prefix for data loading. |
| `headers` | map | Request headers; `${VAR}` is expanded from the environment. |
| `capabilities` | list | Capability tags; scenarios are skipped if their `required_capabilities` aren't all present. |
| `disabled` | bool | If `true`, the engine is skipped at run time. |
| `disabled_reason` | string | Human-readable reason, printed when skipped. |
| `docker` | map | Local container management settings (see below). |

### Docker block

| Field | Type | Notes |
| --- | --- | --- |
| `enabled` | bool | Whether `manage_engines.py` controls this engine. |
| `image` | string | Image reference. |
| `local_image_only` | bool | Don't pull; use a locally built image only. |
| `pull_on_bootstrap` | bool | Pull the image during `bootstrap`. |
| `container_name` | string | Container name to create/manage. |
| `host_port` / `container_port` | int | Port mapping. |
| `env` | map | Environment variables passed to the container. |
| `health_path` | string | Path probed by the `health` action and health waits. |

### Known capability tags

| Capability | Meaning |
| --- | --- |
| `resident_data_load` | Accepts data preloaded into the server. |
| `resident_execute` | Evaluates against resident (preloaded) data. |
| `inline_bundle_execute` | Accepts data inline in the request payload. |
| `system_cql` | Supports system-level `$cql`. |
| `library_write_once_execute_many` | Supports persisting a library and re-evaluating it. |

## Secrets via environment variables

Header values support `${VAR}` expansion, so credentials stay out of config:

```yaml
headers:
  Authorization: Bearer ${ENGINE_BEARER_TOKEN}
```

Copy `.env.example` to `.env` and export the variables before running. Never
commit real tokens; `local.engines.yaml` is gitignored for this reason.

## Suite file

```yaml
suite_id: TPCQF
description: CQF benchmark split into conformance and capability+performance.
defaults:
  timeout_seconds: 30
  concurrency: 16
  warmup_requests: 10
  requests_per_patient: 1
  selectivity: 0.2
expected_http:
  success: [200, 201]
  unsupported: [400, 404, 405, 409, 410, 415, 422, 501]
  fail: []
scenario_ids:
  - CONF001
  - CAP001-P
  # ...
```

| Field | Notes |
| --- | --- |
| `suite_id` | Identifier used in `run_id` and reports. |
| `description` | Free text. |
| `defaults` | Run defaults (overridable per scenario and by CLI flags). |
| `expected_http` | Default HTTP outcome policy for scenarios without their own. |
| `scenario_ids` | Ordered list of scenario folder names. |

## Scenario file (`scenario.yaml`)

```yaml
id: CAP001-P
name: Count retrieve all of one resource (preload)
test_type: capability          # conformance | capability
kind: compute                  # fetch | compute | write (descriptive)
method: GET                    # nominal HTTP method (adapters may rewrite)
path: /Library/$evaluate       # nominal path (adapters may rewrite)
required_capabilities:
  - resident_data_load
  - resident_execute
selectivity: 0.2               # optional per-scenario override
expected_http:
  success: [200]
  unsupported: [400, 405, 415, 422, 501]
  fail: []
expected_file: expected.yaml   # correctness validators
data_file: data.yaml           # data generation config (Type 2 only)
cql_file: scenario.cql         # CQL source
cql_entrypoint: CountAllCondition   # define to evaluate
query:
  library: Library/BenchCAP001-P|1.0.0
  subject: Patient/{patient_id}
  expression: CountAllCondition
setup:                         # preload flow (Type 2 -P)
  method: POST
  path_role: data
  path: /Bundle
  per_patient: true
  expected_http:
    success: [200, 201]
    unsupported: [400, 422]
    fail: []
restart_after_setup: true      # restart engine before timed execution
```

`{patient_id}` is templated per synthetic patient. `cql_library_id` /
`cql_library_version` may be set explicitly; otherwise they are derived from the
query's `library` reference or the scenario ID.

## Data config (`data.yaml`)

Type 2 scenarios describe how their data is generated:

```yaml
selectivity_source: scenario_or_suite_default
setup:
  mode: resident
  generator:
    type: fsh_mutation
    match_fsh: match.fsh
    variations_fsh: variations.fsh
    mutator_file: mutator.yaml
```

## Validators (`expected.yaml`)

Validators assert correctness on the response. They run only when the status is
in `when_status_in`.

```yaml
when_status_in: [200]
validators:
  - type: not_operation_outcome_error
  - type: min_items
    path: $.parameter[*]
    min: 1
```

| Validator `type` | Key fields | Checks |
| --- | --- | --- |
| `not_operation_outcome_error` | — | No error/fatal `OperationOutcome`, no "evaluation error" parameter. |
| `parameters_has_name` | `name` | A `Parameters.parameter` with `name` exists. |
| `define_present` | `define_name`, `path?` | A named define is present (optionally at a JSON path). |
| `min_items` | `path`, `min` | The JSON path selects at least `min` nodes. |
| `value_type_and_equals` | `path`, `expected_type`, `expected_value?`, `mode?` | Node(s) match a FHIR value type and optional value (`mode: any` \| `all`). |
| `function_result_body_equals` | `name`, `expected_body`, `compare_field?` | A result parameter's body equals the expected body. |
| `tokenized_numeric_equals` | `path`, `expression`, `expected_type?`, `rounding?`, `tolerance?` | A numeric result equals an expression over run context (e.g. `selectivity * scale_factor`). |

JSON paths support a small subset: `$`, dotted fields, `[*]` for arrays, and a
simple `[?(@.field=='value')]` filter.

## Mutator (`mutator.yaml`)

Drives deterministic, selectivity-aware data generation from FSH templates.

```yaml
version: 1
seed: '{patient_id}:{scenario_id}'   # stable seed; same inputs -> same data
total_count: 40                      # resources to generate per patient
include_templates:                   # always-included fixtures (e.g. Patient, ValueSet)
  - PatientTemplate
  - ValueSetTemplate
mix:                                 # ratio of matching vs. non-matching templates
  - template: ConditionMatch
    ratio_from_selectivity: match    # ratio = selectivity
  - template: ConditionNoMatch
    ratio_from_selectivity: nomatch  # ratio = 1 - selectivity
linked_templates:                    # resources generated alongside a template
  ConditionMatch: [ObservationFinal]
  ConditionNoMatch: [ObservationCancelled]
mutations:                           # per-template field operations
  - template: ConditionMatch
    fields:
      - path: id
        op: suffix-counter           # suffix-counter | pick | date-jitter
uniqueness:                          # keys that must be unique across resources
  - [resourceType, id]
```

Mutation operations: `suffix-counter` (append a counter), `pick` (choose from
`values`), and `date-jitter` (shift an ISO datetime within a `days: [min, max]`
range). A `mix` entry can use a fixed `ratio` or derive it from selectivity via
`ratio_from_selectivity: match | nomatch`.

## FSH fixtures (`match.fsh`, `variations.fsh`)

Plain FSH `Instance` definitions that serve as templates for generation. The
parser reads `Instance:` / `InstanceOf:` and `* path = value` lines and supports
values like quoted strings, booleans, numbers, and `Reference(...)`. `{patient_id}`
is templated at generation time.
