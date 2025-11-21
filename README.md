# HCAI OPS

Human-Centric AI Operations: risk prediction, incident detection, alert prioritization, and action recommendations.

## Repository layout
- `backend/` – FastAPI app, models, data, tests, and Dockerfile.
- `frontend/` – Vite + Tailwind UI, nginx config, and Dockerfile.
- `deploy/` – Nginx and systemd deployment artifacts.
- `scripts/` – Helper scripts for local runs and installs.
- `hcai_ops_agent/` – Lightweight agent package and tests.
- `docs/` – MkDocs content for the project documentation site.

## Run locally (Python backend)
```bash
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\Activate.ps1 on Windows
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
- Systemd unit files live in `deploy/systemd/`.
- Nginx reverse proxy config lives in `deploy/nginx/`.
- Compose files mount persistent volumes for logs/storage; see `docker-compose.prod.yml`.

## Agent install on another server/PC
1) Prereqs: Python 3.11+, network access to the API host.
2) Clone and install agent:
```bash
git clone https://github.com/visezion/HCAIOPS.git
cd HCAIOPS
python -m venv venv && source venv/bin/activate  # Windows: .\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -e hcai_ops_agent
```
3) Run the agent (example):
```bash
cd hcai_ops_agent
python -m hcai_ops_agent.main --api-url http://<api-host>:8000 --api-key <api-key-if-required>
```
4) Service install: use `scripts/install_agent.sh` (Linux) or `scripts/install_agent.ps1` (Windows) as templates to create a venv and register the agent as a service.
