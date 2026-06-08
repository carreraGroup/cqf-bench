# Contributing to cqf-bench

Thank you for contributing. This project uses **pull requests** into `master`;
direct pushes to `master` should be disabled via branch protection (see below).

## Before you open a PR

1. Use **Python 3.10+** (CI uses 3.11).
2. Copy engine config if you run benchmarks locally:
   ```bash
   cp bench/config/engines.example.yaml bench/config/local.engines.yaml
   ```
3. Run the same checks as CI:
   ```bash
   python -m pip install -e .
   python -m compileall scripts
   python scripts/validate_scenarios.py --suite bench/scenarios/tpcqf/suite.yaml
   python -m unittest discover -s tests -v
   ```
4. If you changed the docs site:
   ```bash
   cd docs-site && npm ci && npm run build
   ```

CI workflow: [`.github/workflows/ci.yml`](.github/workflows/ci.yml) — required
status checks are job names **`python`** and **`docs`**.

## Pull request workflow

1. Fork the repository (or branch within the org if you have write access).
2. Create a feature branch from `master`.
3. Open a PR against `master` using the [PR template](.github/pull_request_template.md).
4. Wait for **CI** (`python` + `docs`) to pass.
5. Get review from a maintainer when branch protection requires it.

Maintainers: configure enforcement in
[`.github/BRANCH_PROTECTION.md`](.github/BRANCH_PROTECTION.md).

## Development setup

Optional local Docker override:

```bash
cp docker-compose.override.yml.example docker-compose.override.yml
```

Local-only files (gitignored):

- `bench/config/local.engines.yaml`
- `docker-compose.override.yml`

Environment variables for engine headers: see [`.env.example`](.env.example).

## Adding a scenario (folder-based)

Add a folder under `bench/scenarios/tpcqf/<SCENARIO_ID>/` with:

- `scenario.yaml`
- `scenario.cql` (when CQL is required)
- `expected.yaml`
- `data.yaml` (Type 2 only)
- `match.fsh`, `variations.fsh`, `mutator.yaml` (Type 2 only)

Then list the ID in `bench/scenarios/tpcqf/suite.yaml` `scenario_ids`.

Pre-generate setup payloads when useful:

```bash
scripts/generate_scenario_data.py \
  --suite bench/scenarios/tpcqf/suite.yaml \
  --out data/generated/scenario_payloads \
  --scale 1000
```

Then set `input_bundle_path` or `input_bundle_dir` in scenario `data.yaml`.

## Style expectations

- Keep scenario IDs stable and deterministic.
- Prefer explicit `expected_http` and golden validators in `expected.yaml`.
- Keep setup data deterministic and selectivity-driven where relevant.
- Use `match.fsh` / `variations.fsh` as templates; use `mutator.yaml` for mix,
  linked resources, and `fixed_templates` when the scenario needs them.

## Documentation

User-facing docs live in [`docs-site/`](docs-site/). Update the matching page when
behavior or CLI flags change.

## Code of conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Report issues to
[akastroulis@carrera.io](mailto:akastroulis@carrera.io).
