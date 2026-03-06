# =============================================================================
# Enthropy Trading Platform - Multi-Stage Dockerfile
# =============================================================================
# Build:  docker build -t enthropy-api:latest -f infra/docker/Dockerfile .
# Run:    docker run -p 8000:8000 enthropy-api:latest
# Scan:   trivy image enthropy-api:latest --severity HIGH,CRITICAL
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Build dependencies with Poetry
# ---------------------------------------------------------------------------
ARG PYTHON_VERSION=3.11

FROM python:${PYTHON_VERSION}-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.7.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

ENV PATH="$POETRY_HOME/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libpq-dev \
        git \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && apt-get purge -y --auto-remove curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml poetry.lock* ./

# Install production dependencies only
RUN poetry install --only main --no-root --no-directory \
    && poetry export -f requirements.txt --output requirements.txt --without-hashes

# Copy application source
COPY . .

# Install the project itself
RUN poetry install --only main

# ---------------------------------------------------------------------------
# Stage 2: Runtime
# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS runtime

LABEL maintainer="Enthropy Engineering <eng@enthropy.dev>" \
      description="Enthropy Quantitative Trading Platform API" \
      version="1.0.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app/src" \
    ENVIRONMENT="production" \
    PORT=8000

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        tini \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1001 appuser \
    && useradd --uid 1001 --gid 1001 --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY --from=builder /app/src ./src
COPY --from=builder /app/alembic.ini* ./
COPY --from=builder /app/migrations ./migrations

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/tmp \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose API port
EXPOSE ${PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Use tini as init system for proper signal handling
ENTRYPOINT ["tini", "--"]

# Run with uvicorn
CMD ["python", "-m", "uvicorn", \
     "enthropy.api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--loop", "uvloop", \
     "--http", "httptools", \
     "--access-log", \
     "--log-level", "info"]
