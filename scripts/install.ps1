# Installs HCAI OPS backend locally (PowerShell)
$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install "$repoRoot/backend"
Write-Output "HCAI OPS installed. Run: .\venv\Scripts\Activate.ps1; Set-Location backend; uvicorn hcai_ops.api.server:app --host 0.0.0.0 --port 8000"
