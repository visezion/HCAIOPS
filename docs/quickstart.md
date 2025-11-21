# Quickstart

1) Install dependencies (see Installation).
2) Start the API:
```bash
uvicorn hcai_ops.api.server:app --reload
```
3) Browse to `http://localhost:8000/ui/dashboard`.
4) Hit the health endpoint:
```bash
curl http://localhost:8000/health
```
5) Explore the API docs at `/docs`.
