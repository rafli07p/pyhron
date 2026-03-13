# data_platform/Dockerfile

FROM python:3.12.8-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 && \
    rm -rf /var/lib/apt/lists/*

FROM base AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*
RUN pip install poetry==1.8.2
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false && \
    poetry install --only main --no-interaction --no-ansi

FROM base AS production
COPY --from=builder /usr/local/lib/python3.12/site-packages \
                    /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .

RUN addgroup --system pyhron && \
    adduser --system --ingroup pyhron --no-create-home pyhron && \
    chown -R pyhron:pyhron /app
USER pyhron

CMD ["celery", "-A", "data_platform.tasks.celery_tasks", "worker", \
     "--loglevel=info", "--concurrency=4", \
     "--queues=ingestion,quality,backfill"]
