# Quickstart

## Python backend (dev loop)
```bash
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\Activate.ps1
pip install -e backend
cd backend
uvicorn hcai_ops.api.server:app --host 0.0.0.0 --port 8000 --reload
```
Open `http://localhost:8000/health` to verify, and `http://localhost:8000/docs` for API docs.

## Frontend (optional, live dev)
```bash
cd frontend
npm install
VITE_API_BASE=http://localhost:8000 npm run dev
```
Open the URL printed by Vite (defaults to `http://localhost:5173`).

## Docker (API + UI together)
```bash
docker compose -f docker-compose.prod.yml up --build -d
```
Then browse to `http://localhost` (UI) or `http://localhost:8000/health` (API).
- If port 80 is taken on your host, change the frontend `ports` entry in `docker-compose.prod.yml` (e.g., `8080:80`) and rerun `docker compose up -d`.
