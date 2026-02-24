#!/usr/bin/env bash
set -euo pipefail

ENGINES_FILE="${ENGINES_FILE:-bench/config/engines.example.yaml}"
SUITE_FILE="${SUITE_FILE:-bench/scenarios/tpcqf/suite.yaml}"
SCALES=("${@:-100 10000 1000000}")

for scale in "${SCALES[@]}"; do
  echo "=== Running scale ${scale} ==="
  scripts/run_benchmark.py \
    --engines "$ENGINES_FILE" \
    --suite "$SUITE_FILE" \
    --scale "$scale" \
    --score-mode strict-2xx
done
