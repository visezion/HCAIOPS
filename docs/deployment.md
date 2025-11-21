# Deployment

## Docker Compose
- Development (hot reload backend): `docker compose -f docker-compose.dev.yml up --build`
- Production (API + UI + nginx proxy): `docker compose -f docker-compose.prod.yml up --build -d`

The production stack builds from `backend/` and `frontend/`, exposes API on `8000`, UI on `80/443`, and persists logs/storage via named volumes.

## Systemd (non-docker)
- Place project at `/opt/hcai_ops`
- Run backend from `/opt/hcai_ops/backend`
- Use provided unit files in `deploy/systemd` and adjust paths/domains as needed

## Nginx + TLS
See `deploy/nginx/hcai_ops.conf` for reverse proxying and certbot webroot settings. Replace `hcai.example.com` with your domain and ensure ports 80/443 are open.

## Step-by-step (Docker, live server)
1) Install Docker + Docker Compose on the server.
2) Clone the repo:  
   `git clone https://github.com/visezion/HCAIOPS.git && cd HCAIOPS`
3) Edit `deploy/nginx/hcai_ops.conf` if you need to set your domain (replace `hcai.example.com`) and mount valid certs to `/etc/letsencrypt`.
4) Start the stack:  
   `docker compose -f docker-compose.prod.yml up --build -d`
5) Verify:  
   - API: `curl http://localhost:8000/health`  
   - UI: `http://<server-domain-or-ip>/`
6) Logs and data persist automatically via the `backend_logs` and `backend_storage` volumes.

## Step-by-step (systemd, no Docker)
1) Install Python 3.11+ (and Node 20+ if building the UI locally).
2) `git clone https://github.com/visezion/HCAIOPS.git && cd HCAIOPS`
3) Backend:  
   `python -m venv venv && source venv/bin/activate`  
   `pip install --upgrade pip && pip install -e backend`
4) Optional UI build:  
   `cd frontend && npm install && npm run build` (serve with nginx; proxy API to `127.0.0.1:8000`)
5) Service: Copy and adapt `deploy/systemd/hcai_ops.service` (set `WorkingDirectory=/opt/hcai_ops/backend` and point ExecStart to your venv’s `uvicorn`). Then enable:  
   `sudo systemctl enable --now hcai_ops`
