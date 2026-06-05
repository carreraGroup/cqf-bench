#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/bootstrap_python_env.sh [--venv-dir DIR] [--python BIN] [--recreate]

Creates a Python virtual environment and installs cqf-bench dependencies.

Options:
  --venv-dir DIR   Virtualenv directory (default: .venv)
  --python BIN     Python interpreter to use (default: python3, fallback: python)
  --recreate       Remove existing venv directory before creating
  -h, --help       Show this help message
EOF
}

VENV_DIR=".venv"
PYTHON_BIN=""
RECREATE="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --venv-dir)
      VENV_DIR="${2:-}"
      shift 2
      ;;
    --python)
      PYTHON_BIN="${2:-}"
      shift 2
      ;;
    --recreate)
      RECREATE="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "${PYTHON_BIN}" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "No python interpreter found (python3/python)." >&2
    exit 1
  fi
fi

if [[ "${RECREATE}" == "true" && -d "${VENV_DIR}" ]]; then
  rm -rf "${VENV_DIR}"
fi

echo "Using Python: ${PYTHON_BIN}"
echo "Creating virtualenv: ${VENV_DIR}"
"${PYTHON_BIN}" -m venv "${VENV_DIR}"

# shellcheck disable=SC1090
source "${VENV_DIR}/bin/activate"

echo "Upgrading pip/setuptools/wheel..."
python -m pip install --upgrade pip setuptools wheel

echo "Installing cqf-bench dependencies from pyproject.toml..."
if ! python -m pip install -e .; then
  echo "Editable install failed; falling back to direct dependency install..." >&2
  python -m pip install "PyYAML>=6.0"
fi

echo "Verifying yaml import..."
python - <<'PY'
import yaml
print("PyYAML:", yaml.__version__)
PY

cat <<EOF
Bootstrap complete.

Activate with:
  source ${VENV_DIR}/bin/activate
EOF
