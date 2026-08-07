# Cloud Run Worker

This sample demonstrates how to run a Temporal Worker inside a
[Google Cloud Run](https://cloud.google.com/run) container. It shows:

- Reading Temporal connection config from environment variables.
- Handling **SIGTERM gracefully** — Cloud Run sends SIGTERM and allows 10 seconds
  for the container to exit; the worker drains in-progress tasks before stopping.
- Optional **mTLS** authentication for [Temporal Cloud](https://temporal.io/cloud)
  via base64-encoded certificate/key env vars.

The sample registers a simple greeting Workflow and Activity. The same pattern
applies to any Workflow/Activity definitions.

## Prerequisites

- A [Temporal Cloud](https://temporal.io/cloud) namespace **or** a self-hosted
  Temporal server reachable from Cloud Run (e.g. via VPC connector or Cloud Run
  direct VPC egress).
- [Docker](https://www.docker.com/) for local testing.
- [Google Cloud SDK (`gcloud`)](https://cloud.google.com/sdk) for deployment.
- Python 3.10+

## Files

| File | Description |
|------|-------------|
| `worker.py` | Entry point — connects to Temporal, registers Workflows/Activities, and handles SIGTERM |
| `workflows.py` | Sample Workflow that executes a greeting Activity |
| `activities.py` | Sample Activity that returns a greeting string |
| `starter.py` | Helper script to start a Workflow execution from a local machine |
| `Dockerfile` | Container definition for Cloud Run |
| `deploy.sh` | Builds the image with Cloud Build and deploys to Cloud Run |
| `pyproject.toml` | Standalone project manifest for this sample |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TEMPORAL_ADDRESS` | Yes | `host:port` of the Temporal frontend (e.g. `<ns>.<acct>.tmprl.cloud:7233`) |
| `TEMPORAL_NAMESPACE` | Yes | Temporal namespace (e.g. `<ns>.<acct>`) |
| `TEMPORAL_TASK_QUEUE` | No | Task queue name (default: `cloud-run-task-queue`) |
| `TEMPORAL_TLS_CERT` | For Temporal Cloud | Base64-encoded mTLS client certificate |
| `TEMPORAL_TLS_KEY` | For Temporal Cloud | Base64-encoded mTLS client private key |

For Temporal Cloud, encode your credentials:

```bash
export TEMPORAL_TLS_CERT=$(base64 -i client.pem)
export TEMPORAL_TLS_KEY=$(base64 -i client.key)
```

## Local Development

### 1. Start a local Temporal dev server

```bash
temporal server start-dev
```

### 2. Run the worker

```bash
TEMPORAL_ADDRESS=localhost:7233 TEMPORAL_NAMESPACE=default uv run python worker.py
```

### 3. Start a workflow

In a separate terminal, from inside this directory:

```bash
TEMPORAL_ADDRESS=localhost:7233 TEMPORAL_NAMESPACE=default uv run python starter.py
```

## Docker

### Build

```bash
docker build -t cloud-run-worker .
```

### Run locally (against local dev server)

```bash
docker run --rm \
  -e TEMPORAL_ADDRESS=host.docker.internal:7233 \
  -e TEMPORAL_NAMESPACE=default \
  cloud-run-worker
```

### Run locally (against Temporal Cloud)

```bash
docker run --rm \
  -e TEMPORAL_ADDRESS=<ns>.<acct>.tmprl.cloud:7233 \
  -e TEMPORAL_NAMESPACE=<ns>.<acct> \
  -e TEMPORAL_TLS_CERT="$(base64 -i client.pem)" \
  -e TEMPORAL_TLS_KEY="$(base64 -i client.key)" \
  cloud-run-worker
```

## Deploy to Cloud Run

Use the provided `deploy.sh` script (requires `gcloud` and appropriate IAM
permissions to push to Container Registry and deploy Cloud Run services):

```bash
export TEMPORAL_ADDRESS=<ns>.<acct>.tmprl.cloud:7233
export TEMPORAL_NAMESPACE=<ns>.<acct>

./deploy.sh my-temporal-worker us-central1 my-gcp-project
```

The script:
1. Builds the container image with Cloud Build and pushes to Container Registry.
2. Deploys the Cloud Run service with the necessary env vars.
3. Reads `TEMPORAL_TLS_CERT` and `TEMPORAL_TLS_KEY` from Secret Manager secrets
   named `<service>-tls-cert` and `<service>-tls-key`.

Or run `gcloud run deploy` directly:

```bash
gcloud run deploy my-temporal-worker \
  --image gcr.io/my-gcp-project/my-temporal-worker:latest \
  --region us-central1 \
  --platform managed \
  --no-allow-unauthenticated \
  --set-env-vars "TEMPORAL_ADDRESS=<ns>.<acct>.tmprl.cloud:7233,TEMPORAL_NAMESPACE=<ns>.<acct>" \
  --set-secrets "TEMPORAL_TLS_CERT=my-temporal-worker-tls-cert:latest,TEMPORAL_TLS_KEY=my-temporal-worker-tls-key:latest" \
  --min-instances 1 \
  --no-cpu-throttling
```

Setting `--min-instances 1` ensures the worker is always polling; without it
Cloud Run may scale to zero and leave no worker available for task execution.

### Why a health server?

Cloud Run services must listen on the port named by `$PORT` (default 8080) or the
deploy's startup probe fails and the service never goes healthy. A Temporal worker
only polls Temporal, so `worker.py` runs a tiny HTTP health endpoint in a background
thread purely to satisfy that contract. The `--no-cpu-throttling` flag keeps CPU
allocated between requests so the worker keeps polling, since Cloud Run otherwise
throttles CPU to near zero when no HTTP request is in flight.

## Further Reading

- [Temporal Python SDK documentation](https://python.temporal.io)
- [Temporal Cloud — production worker deployment](https://docs.temporal.io/production-deployment)
- [Cloud Run — container contract](https://cloud.google.com/run/docs/container-contract)
- [Cloud Run — handling signals (SIGTERM)](https://cloud.google.com/run/docs/reference/container-contract#lifecycle)
