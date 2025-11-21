# syntax=docker/dockerfile:1

FROM python:3.13-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    HCAI_ENV=production \
    HCAI_LOG_DIR=/app/data/logs \
    HCAI_STORAGE_DIR=/app/data/storage
WORKDIR /app
RUN useradd -m hcai
COPY --from=builder /usr/local/lib/python3.13 /usr/local/lib/python3.13
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . /app
RUN mkdir -p /app/data/logs /app/data/storage && chown -R hcai:hcai /app
USER hcai
EXPOSE 8000
CMD ["uvicorn", "hcai_ops.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
