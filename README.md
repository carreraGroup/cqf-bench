# cqf-bench

Open benchmark harness for comparing CQF / Clinical Reasoning endpoint behavior and performance across engines.

## Start Here

Use [GETTING_STARTED.md](GETTING_STARTED.md) for a minimal setup and run flow:

1. Stand up CQF Ruler (OSS)
2. Bootstrap Python environment
3. Run generate -> load -> execute

## What This Repository Contains

- `CONF###` scenarios: endpoint conformance checks (untimed)
- `CAP###-P` scenarios: capability/performance with preloaded data
- `CAP###-I` scenarios: capability/performance with inline data

Core files and scripts:

- `bench/scenarios/tpcqf/suite.yaml`
- `bench/scenarios/tpcqf/<SCENARIO_ID>/`
- `bench/config/engines.example.yaml`
- `scripts/run_benchmark.py`
- `scripts/generate_scenario_data.py`
- `scripts/load_test_data.py`
- `scripts/execute_tests.py`
- `scripts/manage_engines.py`
- `scripts/bootstrap_python_env.sh`

## Local Configuration Policy

- Use tracked example files as templates:
  - `bench/config/engines.example.yaml` -> `bench/config/local.engines.yaml`
  - `docker-compose.override.yml.example` -> `docker-compose.override.yml`
- Keep local values in local files only.
- `bench/config/local.engines.yaml` and `docker-compose.override.yml` are gitignored.
- Localhost endpoints in example files are intentional and supported for local development.

## Config Files

| File | Tracked | Purpose |
|---|---|---|
| `bench/config/engines.example.yaml` | Yes | Template engine config with localhost-friendly defaults. |
| `bench/config/local.engines.yaml` | No (gitignored) | Local engine config used for actual runs. |
| `docker-compose.override.yml.example` | Yes | Template Docker override with placeholders only. |
| `docker-compose.override.yml` | No (gitignored) | Local Docker override with environment-specific values. |

## Reporting

For each engine, report tables show three columns per scenario:

- `Result` (`PASS`/`FAIL`)
- `Time` (blank when not pass)
- `Note` (includes correctness-failure reason, endpoint used, and HTTP status)

CAP timing is only counted for correctness-valid successful responses.

`scripts/execute_tests.py` defaults to `--runs 5` and passes this to the runner as repeated scenario executions for averaged timing.

## Candidate Engines

- Mercury
- HAPI CQF Ruler
- Firely-based runtimes
- Smile CDR
- LinuxForHealth FHIR
- Blaze FHIR

## Additional Documentation

- [GETTING_STARTED.md](GETTING_STARTED.md)
- [catalog.md](catalog.md)
- [BENCHMARK_TESTS.md](BENCHMARK_TESTS.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [SECURITY.md](SECURITY.md)
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
