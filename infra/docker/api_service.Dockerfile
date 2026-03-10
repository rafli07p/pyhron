# =============================================================================
# Pyhron API — Multi-Stage Dockerfile
# =============================================================================
FROM python:3.12.8-slim AS builder

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

COPY README.md ./
COPY shared/ ./shared/
COPY services/ ./services/
COPY apps/ ./apps/
COPY proto/ ./proto/
COPY data_platform/ ./data_platform/
COPY strategy_engine/ ./strategy_engine/
COPY commodity_linkage_engine/ ./commodity_linkage_engine/
COPY macro_intelligence/ ./macro_intelligence/
COPY governance_intelligence/ ./governance_intelligence/
RUN poetry install --only main

# ---------------------------------------------------------------------------
FROM python:3.12.8-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 tini curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1001 appuser \
    && useradd --uid 1001 --gid 1001 --shell /bin/bash --create-home appuser

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY --from=builder /app/shared ./shared
COPY --from=builder /app/services ./services
COPY --from=builder /app/apps ./apps
COPY --from=builder /app/proto ./proto
COPY --from=builder /app/data_platform ./data_platform
COPY --from=builder /app/strategy_engine ./strategy_engine
COPY --from=builder /app/commodity_linkage_engine ./commodity_linkage_engine
COPY --from=builder /app/macro_intelligence ./macro_intelligence
COPY --from=builder /app/governance_intelligence ./governance_intelligence
COPY --from=builder /app/pyproject.toml ./

RUN mkdir -p /app/logs && chown -R appuser:appuser /app
USER appuser

EXPOSE ${PORT}

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["tini", "--"]
CMD ["python", "-m", "uvicorn", "services.api.main:app", \
     "--host", "0.0.0.0", "--port", "8000", "--workers", "2", \
     "--log-level", "info"]
