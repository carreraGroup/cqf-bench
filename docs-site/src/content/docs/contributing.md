---
title: Contributing
description: How to add scenarios, onboard engines, and run the validation checks.
---

CQF Bench is community-driven and Apache-2.0 licensed. New scenarios, new engine
adapters, scoring improvements, and documentation fixes are all welcome.

## Development setup

1. Use **Python 3.10+** (CI runs on 3.11).
2. Copy the engine config template:
   ```bash
   cp bench/config/engines.example.yaml bench/config/local.engines.yaml
   ```
3. Optionally copy the Docker override template:
   ```bash
   cp docker-compose.override.yml.example docker-compose.override.yml
   ```
4. These local files are gitignored and where your real values live:
   - `bench/config/local.engines.yaml`
   - `docker-compose.override.yml`
5. Validate scripts and scenarios:
   ```bash
   python -m compileall scripts
   python scripts/validate_scenarios.py --suite bench/scenarios/tpcqf/suite.yaml
   ```

CI runs the same compile + validate steps on every push and pull request, so run
them locally before opening a PR.

## Adding a scenario

Scenarios are folder-based. Create a directory under
`bench/scenarios/tpcqf/<SCENARIO_ID>/` containing:

- `scenario.yaml` — the scenario definition.
- `scenario.cql` — the CQL (when CQL is required).
- `expected.yaml` — correctness validators.
- `data.yaml` — data generation config (Type 2 scenarios only).
- `match.fsh`, `variations.fsh`, `mutator.yaml` — fixtures and the
  selectivity-driven mutator (Type 2 only).

Then add the ID to `scenario_ids` in `bench/scenarios/tpcqf/suite.yaml`. The
validator fails if a scenario folder exists but isn't listed, so don't leave
orphans.

To avoid regenerating setup data during runs, pre-generate payloads:

```bash
python scripts/generate_scenario_data.py \
  --suite bench/scenarios/tpcqf/suite.yaml \
  --out data/generated/scenario_payloads \
  --scale 1000 --phase setup
```

See [Test Cases](/cqf-bench/concepts/test-cases/) and the
[Configuration Reference](/cqf-bench/reference/configuration/) for the full
schemas.

## Adding an engine adapter

To onboard an engine with non-standard API behavior:

1. Add an adapter class implementing the hooks (`adapt_query`, `adapt_payload`,
   `adapt_path`, `adapt_method`, `payload_from_query`), registered under a unique
   `name`. Start from `generic-cqf` and override only what you need.
2. Reference that `name` in the engine's `adapter` field in your engines config.
3. Set the engine's `capabilities` to match what it actually supports.

See [Engine Adapters](/cqf-bench/concepts/engine-adapters/).

## Updating the catalog

`catalog.md` is the editable source of truth for scenario intent and audit
status. When you add or change a scenario, update its row (Intent, Audit Status,
Last Audit, Notes) and keep IDs aligned with the suite.

## Style expectations

- Keep scenario IDs **stable and deterministic**.
- Prefer explicit `expected_http` and `expected.yaml` validators over implicit
  behavior.
- Keep setup data deterministic and selectivity-driven where relevant.
- Use `match.fsh` / `variations.fsh` as canonical fixture templates; use
  `mutator.yaml` for the selectivity mix and uniqueness constraints.
- Python is formatted with Black (line length 100).

## Submitting changes

- Open an issue to discuss substantial additions (new operation families, new
  adapters) before large PRs.
- Keep PRs focused; one scenario set or one adapter per PR is easiest to review.
- Ensure `compileall` and `validate_scenarios.py` pass.
- Follow the repository's
  [Code of Conduct](https://github.com/carreraGroup/cqf-bench/blob/main/CODE_OF_CONDUCT.md)
  and review [SECURITY.md](https://github.com/carreraGroup/cqf-bench/blob/main/SECURITY.md)
  for reporting vulnerabilities.

## Editing these docs

This documentation site lives in
[`docs-site/`](https://github.com/carreraGroup/cqf-bench/tree/main/docs-site). To work on it:

```bash
cd docs-site
npm install
npm run dev
```

Add a page under `docs-site/src/content/docs/`, register it in the `sidebar` array in
`docs-site/astro.config.mjs`, and open a PR. Pushes to `main` deploy automatically to
GitHub Pages via [`.github/workflows/deploy-docs-site.yml`](https://github.com/carreraGroup/cqf-bench/blob/main/.github/workflows/deploy-docs-site.yml).

Code-level notes for maintainers stay in the repository root and [`docs/`](../docs/)
when present — not in this Astro project.
