# Deployment

## Docker Compose
```bash
docker compose build
docker compose up -d
```

## Systemd (non-docker)
- Place project at `/opt/hcai_ops`
- Use provided unit files in `deploy/systemd`

## Nginx + TLS
See the deployment guide for HTTP->HTTPS proxying and certbot instructions.
