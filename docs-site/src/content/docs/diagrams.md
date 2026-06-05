---
title: Diagrams
description: Architecture and workflow diagrams for CQF Bench — workflow, adapters, suite structure, and result scoring.
---

Visual overview of how CQF Bench is structured and how a run flows from suite
definition to reports. Diagrams render in the browser via
[Mermaid](https://mermaid.js.org/) using the docs site's local markdown content
override.

## 1. CQF Bench workflow

**What it shows:** the end-to-end path from suite definition to reports, through
the generate → load → execute phases, with the engine under test on the right.

```mermaid
flowchart LR
  subgraph Define
    S[suite.yaml] --> SC[scenarios]
  end

  subgraph Generate
    SC --> GEN[generate_scenario_data.py]
    GEN --> DATA[(deterministic<br/>FHIR payloads)]
  end

  subgraph Load
    DATA --> LOAD[load_test_data.py]
    LOAD --> ENG[(Engine<br/>under test)]
  end

  subgraph Execute
    SC --> EXEC[execute_tests.py]
    DATA --> EXEC
    EXEC <--> ENG
    EXEC --> SCORE{score:<br/>HTTP + correctness}
  end

  SCORE --> RJSON[results/run_id.json]
  SCORE --> RMD[results/run_id.md]
```

## 2. Engine adapter architecture

**What it shows:** a single engine-neutral scenario is translated by a per-engine
adapter into the concrete request each server expects. Capabilities gate
eligibility; adapters translate the request.

```mermaid
flowchart TB
  SCEN[Engine-neutral scenario<br/>method • path • query • payload]

  SCEN --> CAP{Engine has required<br/>capabilities?}
  CAP -- no --> SKIP[Skip scenario for engine]
  CAP -- yes --> ADP[Adapter]

  subgraph hooks [Adapter hooks]
    direction LR
    AM[adapt_method] --> AP[adapt_path] --> AQ[adapt_query]
    AQ --> APL[adapt_payload] --> PFQ[payload_from_query]
  end

  ADP --> AM
  PFQ --> REQ[Concrete HTTP request]

  REQ --> G[generic-cqf<br/>Blaze / Firely]
  REQ --> H[hapi-cqf-ruler<br/>GET→POST, instance ops]
  REQ --> M[mercury-cqf<br/>canonical normalize]
  REQ --> SM[smile-cdr]
```

## 3. Benchmark suite structure

**What it shows:** how a suite decomposes into the two scenario classes and the
files each scenario folder contains.

```mermaid
flowchart TD
  SUITE[suite.yaml<br/>suite_id • defaults • expected_http • scenario_ids]

  SUITE --> CONF[Type 1 — Conformance<br/>CONF###]
  SUITE --> CAP[Type 2 — Capability + Performance<br/>CAP###-P / CAP###-I]

  CONF --> CFILES[scenario.yaml<br/>scenario.cql<br/>expected.yaml]

  CAP --> PFILES[scenario.yaml<br/>scenario.cql<br/>data.yaml<br/>expected.yaml<br/>match.fsh<br/>variations.fsh<br/>mutator.yaml]

  CAP --> P[-P Preload<br/>resident data + restart]
  CAP --> I[-I Inline<br/>data in request bundle]
```

## 4. Result comparison flow

**What it shows:** how per-request outcomes roll up into the side-by-side matrices,
emphasizing that timing only flows from PASS rows.

```mermaid
flowchart LR
  REQ[Per-request outcome] --> CLASS{Classify by<br/>expected_http}

  CLASS -->|2xx| OK[success]
  CLASS -->|422| UNS[unsupported]
  CLASS -->|other 4xx| WARN[warning]
  CLASS -->|5xx / timeout| FAIL[fail]

  OK --> VAL{Correctness<br/>validators pass?}
  VAL -- yes --> PASS[PASS<br/>+ record timing]
  VAL -- no --> XFAIL[FAIL<br/>no timing]

  PASS --> MATRIX[Engine column group:<br/>Result • Time • Note]
  XFAIL --> MATRIX
  UNS --> MATRIX
  WARN --> MATRIX
  FAIL --> MATRIX

  MATRIX --> CMP[Side-by-side matrix<br/>across engines]
```

## Editing diagrams

The Mermaid blocks above are the source of truth. To change a diagram, edit this
page and run `npm run dev` in `docs-site/` to preview. For static SVG exports
(e.g. for slides), use the [Mermaid Live Editor](https://mermaid.live/) or the
[`mmdc` CLI](https://github.com/mermaid-js/mermaid-cli).

Mermaid rendering is implemented in
`docs-site/src/components/MarkdownContent.astro` and applies to fenced code
blocks with language `mermaid`.
