# Installs HCAI OPS agent (PowerShell)
python -m venv agent-venv
.\agent-venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install .
Write-Output "Configure agent token and API URL. Use Task Scheduler or services for auto-start."
