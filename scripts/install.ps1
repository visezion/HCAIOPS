# Installs HCAI OPS locally (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install .
Write-Output "HCAI OPS installed. Run: .\venv\Scripts\Activate.ps1; uvicorn hcai_ops.api.server:app --host 0.0.0.0 --port 8000"
