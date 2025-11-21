#!/usr/bin/env bash
# Installs HCAI OPS backend locally
set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install "${REPO_ROOT}/backend"
echo "HCAI OPS installed. Run: source venv/bin/activate && cd backend && uvicorn hcai_ops.api.server:app --host 0.0.0.0 --port 8000"
