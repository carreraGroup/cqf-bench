---
title: Engine Adapters
description: How adapters normalize per-engine API differences so one scenario runs everywhere.
---

CQF and Clinical Reasoning servers accept the same logical request in different
ways. One engine wants `POST /Library/{id}/$evaluate` with a `Parameters` body;
another wants `GET /Library/$evaluate` with query parameters; a third needs the
`library` canonical normalized or removed to avoid resolver mismatches. An
**adapter** encapsulates these differences so a single scenario definition runs
unchanged across engines.

## Selecting an adapter

Each engine entry names its adapter:

```yaml
engines:
  - name: hapi-cqf-ruler-local
    adapter: hapi-cqf-ruler
    base_url: http://localhost:8081
    cqf_base_path: /fhir
    # ...
```

Built-in adapters:

| Adapter | Intended engine |
| --- | --- |
| `generic-cqf` | A baseline CQF server with no special handling (also used for Blaze, Firely-style endpoints). |
| `mercury-cqf` | Mercury — library/measure canonical normalization, data bundle reshaping. |
| `hapi-cqf-ruler` | HAPI CQF Ruler — GET→POST promotion, instance-level operation rewriting. |
| `smile-cdr` | Smile CDR. |
| `google-cql` | google/cql (requires a wrapper service; disabled by default). |

If an adapter name is unknown, the harness falls back to `generic-cqf`.

## The adapter interface

An adapter is a small class with hooks the runner calls while building each
request. Conceptually:

```python
class EngineAdapter:
    name = "generic-cqf"

    def adapt_query(self, scenario, query):
        # Rewrite/strip query parameters.
        return query

    def adapt_payload(self, scenario, payload, phase="main"):
        # Rewrite the request body (e.g. reshape Bundle, normalize canonicals).
        return payload

    def adapt_path(self, scenario, path, phase="main", payload=None):
        # Rewrite the URL path (e.g. type-level -> instance-level operation).
        return path

    def adapt_method(self, scenario, method, phase="main", payload=None):
        # Rewrite the HTTP method (e.g. promote GET to POST).
        return method

    def payload_from_query(self, scenario, patient_id, phase="main"):
        # Synthesize a Parameters body from query params when promoting GET->POST.
        return None
```

`phase` is `"setup"` during the load phase and `"main"` during execution, so an
adapter can treat preloaded data and request-time payloads differently.

The base `generic-cqf` adapter is a no-op: it passes everything through
unchanged.

## What adapters do in practice

A few concrete examples drawn from the built-in adapters:

- **GET → POST promotion** (`hapi-cqf-ruler`): for operations the server only
  exposes via POST (e.g. `/Library/$evaluate`, `/Measure/$evaluate-measure`), the
  adapter promotes the method and synthesizes a `Parameters` body from the query
  parameters.
- **Type-level → instance-level rewriting** (`hapi-cqf-ruler`, `mercury-cqf`):
  rewrites `/Library/$evaluate` to `/Library/{id}/$evaluate` (and the measure
  operations to their instance forms), dropping now-redundant `library` /
  `measure` parameters from the body to avoid canonical/system mismatches.
- **Data bundle reshaping** (`mercury-cqf`): converts a `transaction` Bundle used
  for setup into the `collection` shape the engine expects, and routes it to the
  engine's data endpoint.
- **Canonical normalization** (`mercury-cqf`): normalizes a `library` canonical
  (and derives one from a `measure` reference when missing) so the engine's
  resolver matches the preloaded resources.

These rewrites are deliberately confined to adapters. Scenarios stay
engine-neutral; only the adapter knows an engine's quirks.

## Capabilities gate, adapters translate

It's worth distinguishing two mechanisms:

- **Capabilities** decide *whether* a scenario runs against an engine. If the
  engine doesn't declare a scenario's `required_capabilities`, the scenario is
  skipped.
- **Adapters** decide *how* a scenario runs once it's eligible — the concrete
  path, method, and payload for that engine.

## Adding an adapter

To onboard a new engine with non-standard behavior:

1. Add an adapter class implementing the hooks above, registered under a unique
   `name`.
2. Reference that `name` in the engine's `adapter` field.
3. Set the engine's `capabilities` to match what it actually supports.

Start from `generic-cqf` and override only the hooks you need. See
[Add an engine](/cqf-bench/guides/add-an-engine/) for registering an endpoint and
[Contributing](/cqf-bench/contributing/#adding-an-engine-adapter) for submitting a
new adapter.
