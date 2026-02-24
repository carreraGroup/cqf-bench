# Contributing to cqf-bench

## Development setup

1. Use Python 3.10+.
2. Copy engine config:
   ```bash
   cp bench/config/engines.example.yaml bench/config/local.engines.yaml
   ```
3. Optional local Docker override:
   ```bash
   cp docker-compose.override.yml.example docker-compose.override.yml
   ```
4. Local-only files are gitignored:
   - `bench/config/local.engines.yaml`
   - `docker-compose.override.yml`
5. Validate scenarios and scripts:
   ```bash
   python -m compileall scripts
   scripts/validate_scenarios.py --suite bench/scenarios/tpcqf/suite.yaml
   ```

## Adding a scenario (folder-based)

Add a new folder under `bench/scenarios/tpcqf/<SCENARIO_ID>/` with:

- `scenario.yaml`
- `query.cql` (when CQL is required)
- `data.yaml`
- `expected.yaml`
- `match.fsh`
- `variations.fsh`
- `mutator.yaml`

Then list the ID in `bench/scenarios/tpcqf/suite.yaml` `scenario_ids`.

To avoid regenerating setup data during benchmark runs, pre-generate payload files with:

```bash
scripts/generate_scenario_data.py --suite bench/scenarios/tpcqf/suite.yaml --out data/generated/scenario_payloads --scale 1000 --phase setup
```

Then set `input_bundle_path` or `input_bundle_dir` in scenario `data.yaml`.

## Style expectations

- Keep scenario IDs stable and deterministic.
- Prefer explicit `expected_http` and `expected.yaml` validators.
- Keep setup data deterministic and selectivity-driven where relevant.
- Use `match.fsh` and `variations.fsh` as canonical fixture templates; use `mutator.yaml` for selectivity mix and uniqueness constraints.
