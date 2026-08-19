# syntax=docker/dockerfile:1

# NOTE: This image builds against a released `temporalio[cloud-run-worker-otel]`.
# While the plugin is unreleased, `pyproject.toml` uses a temporary local path
# source for `temporalio` (`../../sdk-python`), which is OUTSIDE this build
# context and therefore not available here. Before building the container,
# replace that source with the first released version (or a pushed git rev) and
# regenerate `uv.lock` with `uv lock`, then restore the `uv.lock` copy and the
# `--frozen` flag below.

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
COPY --chown=app:app __init__.py worker.py workflow.py /app/gcp_cloud_run/

USER app
CMD ["python", "-m", "gcp_cloud_run.worker"]
