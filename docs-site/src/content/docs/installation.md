---
title: Installation
description: Prerequisites, repository setup, and the Python environment for CQF Bench.
---

CQF Bench is distributed as a Git repository of Python scripts and YAML
configuration. There is no package to install from a registry today; you run it
from a checkout of the repo.

## Prerequisites

| Requirement | Notes |
| --- | --- |
| **Python 3.9+** | The scripts target 3.9+; CI runs on 3.11. |
| **Git** | To clone the repository. |
| **Docker** (recommended) | Used by `manage_engines.py` to run target engines locally. Optional if you point at remote endpoints. |

The only Python runtime dependency is **PyYAML**.

## 1. Clone the repository

```bash
git clone https://github.com/carreraGroup/cqf-bench.git
cd cqf-bench
```

## 2. Bootstrap the Python environment

The bootstrap script creates a `.venv` virtual environment and installs
dependencies:

```bash
scripts/bootstrap_python_env.sh --recreate
source .venv/bin/activate
```

If you prefer to manage the environment yourself:

```bash
python -m venv .venv
source .venv/bin/activate
pip install PyYAML
```

## 3. Create local configuration

CQF Bench separates tracked example files from local, gitignored files so that
machine-specific values never get committed.

```bash
# Engine configuration
cp bench/config/engines.example.yaml bench/config/local.engines.yaml

# Optional Docker overrides for local resource limits / images
cp docker-compose.override.yml.example docker-compose.override.yml
```

| File | Tracked | Purpose |
| --- | --- | --- |
| `bench/config/engines.example.yaml` | Yes | Template engine config with localhost-friendly defaults. |
| `bench/config/local.engines.yaml` | No (gitignored) | Local engine config used for actual runs. |
| `docker-compose.override.yml.example` | Yes | Template Docker override with placeholders only. |
| `docker-compose.override.yml` | No (gitignored) | Local Docker override with environment-specific values. |

See the [Configuration Reference](/cqf-bench/reference/configuration/) for the
full schema of these files.

## 4. Provide credentials via environment variables

Engine headers support `${VAR}` expansion, so secrets stay out of config files.
Copy the example env file and fill in real values:

```bash
cp .env.example .env
# then export the variables into your shell, e.g.
export ENGINE_BEARER_TOKEN="..."   # set when your engine requires auth
```

For example, a remote engine in your config might reference a token:

```yaml
headers:
  Authorization: Bearer ${ENGINE_BEARER_TOKEN}
```

## 5. Stand up an engine

The fastest path to a working engine is the open-source HAPI CQF Ruler image:

```bash
python scripts/manage_engines.py bootstrap \
  --engines bench/config/local.engines.yaml \
  --engine hapi-cqf-ruler-local

python scripts/manage_engines.py health \
  --engines bench/config/local.engines.yaml \
  --engine hapi-cqf-ruler-local
```

The `manage_engines.py` actions — `pull`, `build`, `up`, `down`, `status`,
`health`, and `bootstrap` — operate on engines whose `docker.enabled` is `true`.
Engines pointed at remote endpoints (Docker disabled) are managed outside CQF
Bench; you only need them to be reachable.

## 6. Verify your setup

Validate that the scenario suite is well-formed and that all scripts compile:

```bash
python -m compileall scripts
python scripts/validate_scenarios.py --suite bench/scenarios/tpcqf/suite.yaml
```

A successful validation prints `Scenario validation OK: <N> scenarios in <path>`.

:::note
CQF Bench is invoked via `python scripts/...` from a clone of this repository.
There is no published `pip` or `pipx` package yet.
:::

## Next steps

- [Getting Started](/cqf-bench/getting-started/) — run the suite end to end.
- [Core Concepts](/cqf-bench/concepts/) — understand the model before scaling up.
