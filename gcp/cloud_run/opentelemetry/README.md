# Google Cloud Run OpenTelemetry Worker

Run a Temporal Worker on a [Google Cloud Run worker
pool](https://cloud.google.com/run/docs/worker-pools) with
`temporalio.contrib.gcp.cloud_run.opentelemetry.OpenTelemetryPlugin`. It exports
Temporal Core metrics and traces over OTLP/gRPC to a Google-Built OpenTelemetry
Collector sidecar, which forwards traces to the Cloud Telemetry API and metrics
to Google Managed Service for Prometheus. Endpoint, service name (from
`CLOUD_RUN_WORKER_POOL`), tracer provider, and 60s metric export are plugin
defaults; `worker.py` opts into `add_temporal_spans=True` for operation spans.

Prerequisites: a Temporal Cloud namespace and API key; a Google Cloud project
with billing and an authenticated `gcloud` CLI; `envsubst` (`gettext` package).
Worker pools bill continuously, so run scale-to-zero (step 6) after testing.

## Deploy

Run from the repository root, with your own values:

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

# 1. Enable APIs, create the Artifact Registry repo and the runtime service account.
gcloud services enable artifactregistry.googleapis.com cloudbuild.googleapis.com \
  monitoring.googleapis.com run.googleapis.com secretmanager.googleapis.com \
  telemetry.googleapis.com --project "$PROJECT_ID"
gcloud artifacts repositories create "$REPOSITORY" --location "$REGION" \
  --repository-format docker --project "$PROJECT_ID"

# 2. Grant the service account the collector's telemetry roles.
for role in roles/logging.logWriter roles/monitoring.metricWriter roles/telemetry.tracesWriter; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member "serviceAccount:${SERVICE_ACCOUNT_EMAIL}" --role "$role"
done

# 3. Store the API key and collector config as secrets the service account can read.
gcloud secrets create "$TEMPORAL_API_KEY_SECRET" --data-file "$TEMPORAL_API_KEY_FILE" --project "$PROJECT_ID"
gcloud secrets create "$COLLECTOR_CONFIG_SECRET" \
  --data-file gcp/cloud_run/opentelemetry/collector-config.yaml --project "$PROJECT_ID"
for secret in "$TEMPORAL_API_KEY_SECRET" "$COLLECTOR_CONFIG_SECRET"; do
  gcloud secrets add-iam-policy-binding "$secret" \
    --member "serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role roles/secretmanager.secretAccessor --project "$PROJECT_ID"
done

# 4. Build the image (build context is the sample dir, keeping credentials out).
gcloud builds submit gcp/cloud_run/opentelemetry --region "$REGION" \
  --tag "$WORKER_IMAGE" --project "$PROJECT_ID"

# 5. Render and deploy the two-container worker pool.
envsubst < gcp/cloud_run/opentelemetry/worker-pool.yaml > /tmp/worker-pool.yaml
gcloud run worker-pools replace /tmp/worker-pool.yaml --project "$PROJECT_ID"

# 6. Scale to zero when done to stop compute charges.
gcloud run worker-pools update "$WORKER_POOL" --instances 0 \
  --region "$REGION" --project "$PROJECT_ID"
```

## Run a Workflow and verify

```bash
uv sync --group gcp-cloud-run-opentelemetry
TEMPORAL_API_KEY="$(cat "$TEMPORAL_API_KEY_FILE")" \
  uv run --group gcp-cloud-run-opentelemetry python -m gcp.cloud_run.opentelemetry.starter
```

The starter prints `Hello, Temporal!`. In Google Cloud, Trace Explorer then shows
`RunWorkflow:GreetingWorkflow` (with `service.name` = the worker-pool name) and
Metrics Explorer shows
`prometheus.googleapis.com/temporal_workflow_completed_total/counter`.
