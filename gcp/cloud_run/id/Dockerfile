# syntax=docker/dockerfile:1

# The git-pinned temporalio compiles the Rust core; drop this builder for a Python base once the plugin ships on PyPI.
FROM rust:1.91.0-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.8.15 /uv /uvx /bin/

RUN apt-get update \
    && apt-get install --no-install-recommends --yes \
        build-essential \
        ca-certificates \
        git \
        libprotobuf-dev \
        pkg-config \
        protobuf-compiler \
        python3 \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON=/usr/bin/python3

WORKDIR /app
COPY pyproject.toml ./
RUN uv sync --no-dev

FROM debian:bookworm-slim

ENV PATH=/app/.venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install --no-install-recommends --yes ca-certificates python3 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app \
    && useradd --system --gid app --create-home app

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
# The build context is this sample directory (flat), so recreate the
# gcp/cloud_run/id package path and its parent package markers.
COPY --chown=app:app __init__.py activities.py settings.py worker.py workflows.py /app/gcp/cloud_run/id/
RUN touch /app/gcp/__init__.py /app/gcp/cloud_run/__init__.py \
    && chown -R app:app /app/gcp

USER app
CMD ["python", "-m", "gcp.cloud_run.id.worker"]
