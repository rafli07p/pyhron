# =============================================================================
# Pyhron Celery Worker — Multi-Stage Dockerfile
# =============================================================================
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.8.4 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

ENV PATH="$POETRY_HOME/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl libpq-dev \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && apt-get purge -y --auto-remove curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml poetry.lock* ./
RUN poetry install --only main --no-root --no-directory

COPY shared/ ./shared/
COPY services/ ./services/
COPY data-platform/ ./data-platform/
COPY strategies/ ./strategies/
COPY proto/ ./proto/
RUN poetry install --only main

# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 tini \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1001 appuser \
    && useradd --uid 1001 --gid 1001 --shell /bin/bash --create-home appuser

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY --from=builder /app/shared ./shared
COPY --from=builder /app/services ./services
COPY --from=builder /app/data-platform ./data-platform
COPY --from=builder /app/strategies ./strategies
COPY --from=builder /app/proto ./proto
COPY --from=builder /app/pyproject.toml ./

RUN mkdir -p /app/logs && chown -R appuser:appuser /app
USER appuser

ENTRYPOINT ["tini", "--"]
CMD ["celery", "-A", "data_platform.tasks.celery_tasks:celery_app", \
     "worker", "--loglevel=info", "--queues=ingestion,analytics", \
     "--concurrency=4"]
