#!/usr/bin/env bash
# Installs HCAI OPS locally
set -e
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install .
echo "HCAI OPS installed. Run: source venv/bin/activate && uvicorn hcai_ops.api.server:app --host 0.0.0.0 --port 8000"
