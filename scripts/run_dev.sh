#!/usr/bin/env bash
# chmod 755
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${SCRIPT_DIR}/../backend"

export HCAI_ENV=development
export PYTHONPATH="${BACKEND_DIR}"

cd "${BACKEND_DIR}"
uvicorn hcai_ops.api.server:app --host 0.0.0.0 --port 8000 --reload
