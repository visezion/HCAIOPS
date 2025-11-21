# Installs HCAI OPS agent (PowerShell) with auto Python setup
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $repoRoot "agent-venv"

function Get-PythonCmd {
    foreach ($cmd in @("python", "python3")) {
        if (Get-Command $cmd -ErrorAction SilentlyContinue) { return $cmd }
    }
    return $null
}

function Install-Python {
    Write-Host "Python not found. Attempting installation..."
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install --id Python.Python.3.11 -e --silent
    } elseif (Get-Command choco -ErrorAction SilentlyContinue) {
        choco install python -y
    } else {
        throw "No package manager (winget/choco) found. Install Python 3.11+ manually."
    }
}

$py = Get-PythonCmd
if (-not $py) {
    Install-Python
    $py = Get-PythonCmd
    if (-not $py) { throw "Python installation failed. Install manually and rerun." }
}

& $py -m ensurepip --default-pip *> $null
& $py -m pip install --upgrade pip
& $py -m venv $venvPath

. (Join-Path $venvPath "Scripts/Activate.ps1")
python -m pip install --upgrade pip
python -m pip install -e (Join-Path $repoRoot "hcai_ops_agent")

Write-Output "Agent installed. Add your config JSON (api_url/token) then start: cd hcai_ops_agent; $(Join-Path $venvPath 'Scripts/python.exe') -m hcai_ops_agent.main"
