#!/usr/bin/env bash
# chmod 755
export HCAI_ENV=development
uvicorn hcai_ops.api.server:app --host 0.0.0.0 --port 8000 --reload
