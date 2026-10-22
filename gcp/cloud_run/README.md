# Google Cloud Run Worker

Run a Temporal Worker on a [Google Cloud Run worker
pool](https://cloud.google.com/run/docs/worker-pools) with two GCP plugins on
one client. `temporalio.contrib.gcp.cloud_run.opentelemetry.OpenTelemetryPlugin`
exports Temporal Core metrics and traces over OTLP/gRPC to a Google-Built
OpenTelemetry Collector sidecar, which forwards traces to the Cloud Telemetry API
and metrics to Google Managed Service for Prometheus; endpoint, service name
(from `CLOUD_RUN_WORKER_POOL`), tracer provider, and 60s metric export are plugin
defaults, and `worker.py` opts into `add_temporal_spans=True`.
`temporalio.contrib.gcp.cloud_run.id.CloudRunIdPlugin` sets the client identity
to `<instance_id>@<revision>` from Cloud Run instance metadata, so each container
is individually identifiable as a poller.

`CloudRunIdPlugin` is unreleased, so `pyproject.toml` pins `temporalio` to the
SDK commit that adds it (a git source, which also builds inside the container);
drop the `[tool.uv.sources]` override once it ships on PyPI.

Prerequisites: a Temporal Cloud namespace and API key; a Google Cloud project
with billing and an authenticated `gcloud` CLI; `envsubst` (`gettext` package).
Worker pools bill continuously, so scale to zero after testing (see below).

## Deploy

Run from the repository root. Set your own values (also used by the verify step
below), then run the deploy script:

```bash
export PROJECT_ID=your-project-id REGION=us-central1
export REPOSITORY=temporal-workers WORKER_POOL=temporal-gcp-cloud-run
export SERVICE_ACCOUNT_EMAIL="cloud-run-worker@${PROJECT_ID}.iam.gserviceaccount.com"
export TEMPORAL_NAMESPACE=your-namespace.account-id
export TEMPORAL_ADDRESS="${TEMPORAL_NAMESPACE}.tmprl.cloud:7233"
export TEMPORAL_TASK_QUEUE=gcp-cloud-run
export TEMPORAL_API_KEY_FILE=/secure/path/to/temporal-api-key
export TEMPORAL_API_KEY_SECRET=temporal-api-key TEMPORAL_API_KEY_SECRET_VERSION=1
export COLLECTOR_CONFIG_SECRET=temporal-otel-collector COLLECTOR_CONFIG_SECRET_VERSION=1
export WORKER_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/gcp-cloud-run:v1"
export INSTANCE_COUNT=1

./gcp/cloud_run/deploy.sh
```

`deploy.sh` enables the required APIs; creates the Artifact Registry repo, the
runtime service account, and the API key and collector-config secrets; grants the
telemetry and secret-access roles; then builds the image and deploys the
two-container worker pool. The create steps are one-time and re-run safely.

Worker pools bill continuously, so scale to zero when done testing:

```bash
gcloud run worker-pools update "$WORKER_POOL" --instances 0 \
  --region "$REGION" --project "$PROJECT_ID"
```

## Run a Workflow and verify

```bash
TEMPORAL_API_KEY="$(cat "$TEMPORAL_API_KEY_FILE")" \
  uv run python -m gcp.cloud_run.starter
```

The starter prints `Hello, Temporal!`. In Google Cloud, Trace Explorer shows
`RunWorkflow:GreetingWorkflow` (with `service.name` = the worker-pool name) and
Metrics Explorer shows
`prometheus.googleapis.com/temporal_workflow_completed_total/counter`. In the
Temporal UI, the task queue's pollers report the `<instance_id>@<revision>`
identity set by `CloudRunIdPlugin`.
