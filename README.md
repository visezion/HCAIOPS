# HCAI OPS

Human-Centric AI Operations: risk prediction, incident detection, alert prioritization, and action recommendations.

## Repository layout
- `backend/` - FastAPI app, models, data, tests, and Dockerfile.
- `frontend/` - Vite + Tailwind UI, nginx config, and Dockerfile.
- `deploy/` - Nginx and systemd deployment artifacts.
- `scripts/` - Helper scripts for local runs and installs.
- `hcai_ops_agent/` - Lightweight agent package and tests.
- `docs/` - MkDocs content for the project documentation site.

## Run locally (Python backend)
```bash
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -e backend
cd backend && uvicorn hcai_ops.api.server:app --host 0.0.0.0 --port 8000 --reload
```
- Convenience scripts: `scripts/run_dev.sh` or `scripts/run_prod.sh`.

## Run UI locally
```bash
cd frontend
npm install
npm run dev   # serves the UI; set VITE_API_BASE to point at your backend if needed
```

## Docker
- Development: `docker compose -f docker-compose.dev.yml up --build`
- Production: `docker compose -f docker-compose.prod.yml up --build -d`
  - If host port 80 is busy, remap the frontend port in `docker-compose.prod.yml` (e.g., `8080:80`) and rerun `docker compose up -d`.

## Production deployment (Docker, live server)
1) Prereqs: Docker + Docker Compose, ports 80/443/8000 open, domain DNS pointed at the host for TLS.
2) Clone and enter: `git clone https://github.com/visezion/HCAIOPS.git && cd HCAIOPS`
3) Optional: update `deploy/nginx/hcai_ops.conf` with your domain (replace `hcai.example.com`) and mount valid certs under `/etc/letsencrypt`.
4) Run: `docker compose -f docker-compose.prod.yml up --build -d`
5) Verify: `curl http://localhost:8000/health` (API) and browse `http://<your-domain-or-ip>/` (UI).

## Testing
```bash
python -m pytest
```

## Documentation
```bash
pip install mkdocs mkdocs-material
mkdocs serve
```

## Deployment pointers
- Systemd unit files live in `deploy/systemd/` (update `WorkingDirectory` to `/opt/hcai_ops/backend` if you use that layout).
- Nginx reverse proxy config lives in `deploy/nginx/`.
- Compose files mount persistent volumes for logs/storage; see `docker-compose.prod.yml`.

## Agent install on another server/PC (Windows, macOS, Linux)
Prereqs: Python 3.11+, outbound HTTPS to your API host (e.g., `https://hcaiops.vicezion.com`), and a valid API token.

### 0) Quick auto-install (no Python preinstalled)
- Windows (PowerShell, run as admin if winget/choco prompt): `scripts\install_agent.ps1`
- macOS/Linux: `bash scripts/install_agent.sh`
These scripts attempt to install Python 3.11+ (winget/choco/apt/dnf/yum/brew), recreate a fresh venv if needed, and install the agent. Then jump to step 3 to configure.

### 1) Get the code
```bash
git clone https://github.com/visezion/HCAIOPS.git
cd HCAIOPS
```

### 2) Create a virtualenv and install the agent
- Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -e hcai_ops_agent
```
- macOS/Linux (bash/zsh):
```bash
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -e hcai_ops_agent
```

### 3) Configure the agent endpoint and token
Create the config file (defaults are Windows `C:/ProgramData/HCAI_AGENT/config.json`, macOS/Linux `~/.hcai_agent/config.json`). Example content:
```json
{
  "api_url": "https://hcaiops.vicezion.com",
  "token": "<your-token>",
  "send_intervals": { "heartbeat": 10, "metrics": 15, "logs": 20, "flush": 60 },
  "log_paths": { "linux": ["/var/log/syslog", "/var/log/messages"], "windows": ["Application", "System"] },
  "queue_path": "~/.hcai_agent/queue.db"
}
```
(You can override the path with the env var `HCAI_AGENT_CONFIG_PATH`.)

### 4) Run the agent
```bash
cd hcai_ops_agent
python -m hcai_ops_agent.main
```
The agent will post to `<api_url>/events/ingest`. If TLS is self-signed, trust the cert or use a valid one.

### 5) Optional: run on boot
- Windows: create a Scheduled Task (or use `scripts/install_agent.ps1` as a template) that runs the venv python with `-m hcai_ops_agent.main`.
- macOS/Linux: systemd user service (`scripts/install_agent.sh` as a template) or a launchd plist on macOS.

## Ops quick references
- Verify API: `curl http://localhost:8000/health`
- Docker rebuild prod: `docker compose -f docker-compose.prod.yml build --no-cache && docker compose -f docker-compose.prod.yml up -d`
- Port 80 conflict: stop the conflicting service or remap frontend to another host port in `docker-compose.prod.yml`.
