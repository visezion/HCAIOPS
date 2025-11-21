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
