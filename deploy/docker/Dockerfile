FROM python:3.12-slim AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY pyproject.toml uv.lock ./
COPY src/__init__.py src/__init__.py

RUN pip install --no-cache-dir uv && \
    uv sync --frozen --no-dev --no-install-project

COPY src/ src/

RUN uv sync --frozen --no-dev

FROM python:3.12-slim AS production

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        tini \
    && rm -rf /var/lib/apt/lists/* && \
    rm -rf /var/cache/apt/archives/* /var/lib/apt/lists/*

RUN groupadd -r trust_safety && \
    useradd -r -g trust_safety -d /app -s /sbin/nologin trust_safety

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app/src" \
    APP_MODULE="src.api.app:app" \
    APP_HOST="0.0.0.0" \
    APP_PORT="8000" \
    WORKERS=2 \
    LOG_LEVEL="info" \
    ENVIRONMENT="production"

COPY deploy/docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

COPY src/ /app/src/

RUN chown -R trust_safety:trust_safety /app

USER trust_safety

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["tini", "--"]
CMD ["/app/entrypoint.sh"]
