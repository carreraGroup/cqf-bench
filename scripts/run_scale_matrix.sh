#!/usr/bin/env bash
set -euo pipefail

ENGINES_FILE="${ENGINES_FILE:-bench/config/engines.example.yaml}"
SCALES=("${@:-100 10000 1000000}")

for scale in "${SCALES[@]}"; do
  GENROOT="data/generated/scale_matrix_s${scale}_sel20"
  echo "=== Scale ${scale} (generate → load → execute) ==="
  scripts/run_benchmark.py \
    --run-phase generate \
    --scale "$scale" \
    --selectivity 0.2 \
    --generated-data-root "$GENROOT"
  scripts/load_test_data.py \
    --engines "$ENGINES_FILE" \
    --generated-data-root "$GENROOT"
  scripts/run_benchmark.py \
    --run-phase execute \
    --engines "$ENGINES_FILE" \
    --generated-data-root "$GENROOT" \
    --score-mode strict-2xx
done
