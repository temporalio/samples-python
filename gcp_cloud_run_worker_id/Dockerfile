# syntax=docker/dockerfile:1

# NOTE: the Google Cloud Run metadata helper is not released yet, so
# `pyproject.toml` pins `temporalio` to a local path source (../../sdk-python-2)
# that is OUTSIDE this build context and therefore unavailable here. Before
# building the image, either:
#   * wait for an SDK release that includes the helper and drop the
#     [tool.uv.sources] override so `temporalio` installs from PyPI, or
#   * replace that override with a pushed git revision, e.g.
#       temporalio = { git = "https://github.com/temporalio/sdk-python", branch = "cloud-run-worker-id" }
# Installing `temporalio` from git compiles the Rust core, which is why the
# builder stage below starts from a Rust toolchain image. Once the helper ships
# on PyPI you can install the released wheel and drop the Rust builder entirely.

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
COPY --chown=app:app activities.py settings.py worker.py workflows.py ./

USER app
CMD ["python", "worker.py"]
