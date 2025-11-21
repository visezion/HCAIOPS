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
