# Troubleshooting

## Common checks
- `curl http://localhost:8000/health`
- `docker compose ps`
- `docker logs hcai_ops_api`

## 502 Bad Gateway
- Ensure API container is running
- Check Nginx upstream config

## Certbot challenges
- Verify webroot
- Open ports 80/443
