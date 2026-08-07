FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install runtime dependency
RUN uv pip install --system "temporalio>=1.28.0,<2"

# Copy the cloud_run_worker package
COPY __init__.py activities.py workflows.py worker.py starter.py ./cloud_run_worker/

# The worker polls Temporal, and it also serves a tiny health endpoint on $PORT
# (default 8080) so Cloud Run's startup probe passes. See worker.py.
EXPOSE 8080

CMD ["python", "-m", "cloud_run_worker.worker"]
