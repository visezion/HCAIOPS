# Installation

## Prerequisites
- Python 3.11+
- Git
- Optional: Docker and Docker Compose
- Optional (UI dev): Node 20+ and npm

## Backend (FastAPI) setup
```bash
git clone https://github.com/your-org/hcai_ops.git
cd hcai_ops
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -e backend
cd backend
uvicorn hcai_ops.api.server:app --host 0.0.0.0 --port 8000 --reload
```

## Frontend (Vite) setup
```bash
cd frontend
npm install
npm run dev  # set VITE_API_BASE to your backend URL if needed
```

## Docker (API + UI)
```bash
docker compose -f docker-compose.prod.yml up --build -d
```
