#!/usr/bin/env bash
# Installs HCAI OPS agent
set -e
python -m venv agent-venv
source agent-venv/bin/activate
pip install --upgrade pip
pip install .
echo "Configure your agent token and API URL, then run agent ping/report. Set up systemd or cron for auto-start."
