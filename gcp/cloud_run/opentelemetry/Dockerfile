# syntax=docker/dockerfile:1

FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.8.15 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app
COPY pyproject.toml ./
RUN uv sync --no-dev

FROM python:3.13-slim

ENV PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1

RUN groupadd --system app \
    && useradd --system --gid app --create-home app

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
# The build context is this sample directory (flat); recreate the package path.
COPY --chown=app:app __init__.py settings.py worker.py workflow.py /app/gcp/cloud_run/opentelemetry/
RUN touch /app/gcp/__init__.py /app/gcp/cloud_run/__init__.py \
    && chown -R app:app /app/gcp

USER app
CMD ["python", "-m", "gcp.cloud_run.opentelemetry.worker"]
