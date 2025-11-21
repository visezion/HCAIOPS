#!/usr/bin/env bash
# Installs HCAI OPS agent with auto Python setup (Linux/macOS)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${REPO_ROOT}/agent-venv"

ensure_python() {
  if command -v python3 >/dev/null 2>&1; then
    echo "Using python3"
    PYTHON=python3
    return
  fi
  if command -v python >/dev/null 2>&1; then
    echo "Using python"
    PYTHON=python
    return
  fi
  echo "Python not found. Attempting to install..."
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip
    PYTHON=python3
    return
  fi
  if command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y python3 python3-venv python3-pip
    PYTHON=python3
    return
  fi
  if command -v yum >/dev/null 2>&1; then
    sudo yum install -y python3 python3-venv python3-pip
    PYTHON=python3
    return
  fi
  if command -v brew >/dev/null 2>&1; then
    brew install python
    PYTHON=python3
    return
  fi
  echo "No supported package manager found. Install Python 3.11+ manually and rerun."
  exit 1
}

ensure_python
"$PYTHON" - <<'PY'
import sys
import os
if sys.version_info < (3, 11):
    print(f"Python {sys.version.split()[0]} is too old; need 3.11+.", file=sys.stderr)
    sys.exit(1)
PY

# Recreate venv if it exists (handles corrupted envs)
if [ -d "$VENV_DIR" ]; then
  rm -rf "$VENV_DIR"
fi
"$PYTHON" -m ensurepip --default-pip >/dev/null 2>&1 || true
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
pip install --upgrade pip
pip install -e "${REPO_ROOT}/hcai_ops_agent"

echo "Agent installed. Add your config JSON (api_url/token) and start with: cd hcai_ops_agent && ${VENV_DIR}/bin/python -m hcai_ops_agent.main"
