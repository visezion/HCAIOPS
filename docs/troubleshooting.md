# Troubleshooting

## Common checks
- `curl http://localhost:8000/health` (API live)
- `docker compose ps` (service states)
- `docker logs hcai_ops_backend` (API), `docker logs hcai_ops_frontend` (UI), `docker logs hcai_ops_nginx` (proxy)

## 502 Bad Gateway
- Ensure API container is running (`hcai_ops_backend`)
- Check Nginx upstream config/domain (`deploy/nginx/hcai_ops.conf`)

## Certbot challenges
- Verify webroot mapping (`/var/www/certbot`)
- Open ports 80/443 and ensure DNS points at the host
