# =============================================================================
# Pyhron Trading Platform - Multi-Stage Dockerfile
# =============================================================================
# Build:  docker build -t pyhron-api:latest -f infra/docker/Dockerfile .
# Run:    docker run -p 8000:8000 pyhron-api:latest
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Install dependencies with Poetry
# ---------------------------------------------------------------------------
FROM python:3.12.8-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.8.4 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

ENV PATH="$POETRY_HOME/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libpq-dev \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && apt-get purge -y --auto-remove curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml poetry.lock* ./

# Install production dependencies only (skip optional ml group)
RUN poetry install --only main --no-root --no-directory

# Copy application source
COPY shared/ ./shared/
COPY services/ ./services/
COPY apps/ ./apps/
COPY strategies/ ./strategies/

# Install the project itself (makes packages importable)
RUN poetry install --only main

# ---------------------------------------------------------------------------
# Stage 2: Runtime
# ---------------------------------------------------------------------------
FROM python:3.12.8-slim AS runtime

LABEL maintainer="Pyhron Engineering <eng@pyhron.dev>" \
      description="Pyhron Quantitative Trading Platform API" \
      version="0.1.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT="production" \
    PORT=8000

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        tini \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1001 appuser \
    && useradd --uid 1001 --gid 1001 --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY --from=builder /app/shared ./shared
COPY --from=builder /app/services ./services
COPY --from=builder /app/apps ./apps
COPY --from=builder /app/strategies ./strategies
COPY --from=builder /app/pyproject.toml ./

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/tmp \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

EXPOSE ${PORT}

# Health check using stdlib only (no curl needed)
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Use tini as init system for proper signal handling
ENTRYPOINT ["tini", "--"]

# Run the FastAPI application
CMD ["python", "-m", "uvicorn", \
     "services.api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--log-level", "info"]
