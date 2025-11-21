# syntax=docker/dockerfile:1

FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies into a staging prefix to keep the runtime image slim
COPY pyproject.toml .
COPY hcai_ops ./hcai_ops
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install .

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HCAI_ENV=production \
    HCAI_LOG_DIR=/app/data/logs \
    HCAI_STORAGE_DIR=/app/data/storage

WORKDIR /app

RUN groupadd -r hcai && useradd -r -g hcai hcai

# Python dependencies from the builder image
COPY --from=builder /install /usr/local

# Application source and assets
COPY . .

RUN mkdir -p /app/data/logs /app/data/storage \
    && chown -R hcai:hcai /app

USER hcai

EXPOSE 8000

CMD ["uvicorn", "hcai_ops.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
