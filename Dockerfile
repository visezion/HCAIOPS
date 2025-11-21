# syntax=docker/dockerfile:1

ARG BACKEND_DIR=backend

FROM python:3.11-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY ${BACKEND_DIR}/pyproject.toml ./
COPY ${BACKEND_DIR}/hcai_ops ./hcai_ops
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install .

FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    HCAI_ENV=production \
    HCAI_LOG_DIR=/app/data/logs \
    HCAI_STORAGE_DIR=/app/data/storage
WORKDIR /app
RUN useradd -m hcai
COPY --from=builder /install /usr/local
COPY ${BACKEND_DIR}/hcai_ops ./hcai_ops
COPY ${BACKEND_DIR}/web ./web
COPY ${BACKEND_DIR}/models_store ./models_store
COPY ${BACKEND_DIR}/storage ./storage
COPY ${BACKEND_DIR}/sample_data ./sample_data
COPY ${BACKEND_DIR}/data ./data
RUN mkdir -p /app/data/logs /app/data/storage && chown -R hcai:hcai /app
USER hcai
EXPOSE 8000
CMD ["uvicorn", "hcai_ops.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
