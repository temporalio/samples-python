# Google Cloud Run OpenTelemetry Worker

This sample runs a long-lived Temporal Worker in a [Google Cloud Run worker
pool](https://cloud.google.com/run/docs/worker-pools) and sends traces and
Temporal Core metrics to a Google-Built OpenTelemetry Collector sidecar.

The worker uses `temporalio.contrib.gcp.cloud_run.OpenTelemetryPlugin` to
configure:

- OTLP gRPC export to `http://localhost:4317`.
- `service.name` from the Cloud Run-provided `CLOUD_RUN_WORKER_POOL` variable.
- A replay-safe OpenTelemetry tracer provider.
- Temporal Core metrics with a 60-second export interval.

Those are plugin defaults. This sample opts into `add_temporal_spans=True` so
operations such as `RunWorkflow:GreetingWorkflow` are traced. The collector
detects the Google Cloud resource, authenticates through the worker pool's
service account, exports traces through the Google Cloud Telemetry API, and
exports metrics to Google Managed Service for Prometheus.

> The Cloud Run plugin is not released yet. Both `pyproject.toml` files (this
> directory and the repository root) currently use a temporary local
> `[tool.uv.sources]` path to the SDK checkout at `../sdk-python`. Replace those
> source pins with the first released `temporalio[cloud-run-worker-otel]`
> version before merging this sample. The container build additionally requires
> a released (or pushed git) SDK and a regenerated `uv.lock`, because the local
> path is not available inside the Docker build context.

## Files

| File | Purpose |
|------|---------|
| `workflow.py` | Greeting Workflow and Activity |
| `worker.py` | Plugin setup, collector readiness, Worker, and graceful shutdown |
| `starter.py` | Local client that starts a unique Workflow Execution |
| `collector-config.yaml` | Collector receiver, GCP detection, processing, and exporters |
| `worker-pool.yaml` | Environment-substituted two-container WorkerPool manifest |
| `Dockerfile` | Reproducible, non-root worker image |
| `pyproject.toml` | Standalone dependencies used by the container build |

## Prerequisites

- A Temporal Cloud namespace and API key.
- A Google Cloud project with billing enabled.
- The Google Cloud CLI, authenticated to that project.
- Permission to manage Cloud Run worker pools, builds, Artifact Registry,
  service accounts, IAM bindings, and Secret Manager secrets.
- `uv` for running the starter locally.
- `envsubst` for rendering the manifest. It is preinstalled in Cloud Shell and
  is available in the `gettext` package on many systems.

Cloud Run worker pools use manual scaling. Active instances are billed
continuously, so always complete the scale-to-zero step after testing.

## 1. Choose project-neutral resource names

Run the commands from the repository root. The values below are examples; use
names appropriate for your project and namespace.

```bash
export PROJECT_ID=your-project-id
export REGION=us-central1
export REPOSITORY=temporal-workers
export WORKER_POOL=temporal-gcp-cloud-run-worker
export SERVICE_ACCOUNT=temporal-gcp-cloud-run-worker
export SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com"

export TEMPORAL_NAMESPACE=your-namespace.account-id
export TEMPORAL_ADDRESS="${TEMPORAL_NAMESPACE}.tmprl.cloud:7233"
export TEMPORAL_TASK_QUEUE=gcp-cloud-run
export TEMPORAL_API_KEY_FILE=/secure/path/to/temporal-api-key

export TEMPORAL_API_KEY_SECRET=temporal-api-key
export COLLECTOR_CONFIG_SECRET=temporal-otel-collector-config
export TEMPORAL_API_KEY_SECRET_VERSION=1
export COLLECTOR_CONFIG_SECRET_VERSION=1

export WORKER_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/gcp-cloud-run:sample-v1"
```

The API key file must not be inside the repository or Docker build context.

## 2. Enable APIs and create the runtime identity

```bash
gcloud services enable \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  monitoring.googleapis.com \
  run.googleapis.com \
  secretmanager.googleapis.com \
  telemetry.googleapis.com \
  --project "$PROJECT_ID"

gcloud artifacts repositories create "$REPOSITORY" \
  --location "$REGION" \
  --project "$PROJECT_ID" \
  --repository-format docker

gcloud iam service-accounts create "$SERVICE_ACCOUNT" \
  --display-name "Temporal Cloud Run worker" \
  --project "$PROJECT_ID"
```

Grant only the roles needed by the collector and Cloud Run logging:

```bash
for role in \
  roles/logging.logWriter \
  roles/monitoring.metricWriter \
  roles/telemetry.tracesWriter
do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member "serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role "$role"
done
```

## 3. Store both values in Secret Manager

Create the API-key secret directly from its file. Do not place the key on a
command line or copy it into the manifest.

```bash
gcloud secrets create "$TEMPORAL_API_KEY_SECRET" \
  --data-file "$TEMPORAL_API_KEY_FILE" \
  --project "$PROJECT_ID" \
  --replication-policy automatic

gcloud secrets create "$COLLECTOR_CONFIG_SECRET" \
  --data-file gcp_cloud_run/collector-config.yaml \
  --project "$PROJECT_ID" \
  --replication-policy automatic
```

If a secret already exists, add a version instead and update the corresponding
numeric version variable:

```bash
gcloud secrets versions add "$COLLECTOR_CONFIG_SECRET" \
  --data-file gcp_cloud_run/collector-config.yaml \
  --project "$PROJECT_ID"
```

Grant the runtime identity access only to these two secrets:

```bash
for secret in "$TEMPORAL_API_KEY_SECRET" "$COLLECTOR_CONFIG_SECRET"
do
  gcloud secrets add-iam-policy-binding "$secret" \
    --member "serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role roles/secretmanager.secretAccessor \
    --project "$PROJECT_ID"
done
```

The worker strips surrounding whitespace from `TEMPORAL_API_KEY` because
Secret Manager preserves a trailing newline present in the source file.

## 4. Build the worker image

The build context is the sample directory, which keeps credentials and the
rest of the repository out of the image build.

```bash
gcloud builds submit gcp_cloud_run \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --tag "$WORKER_IMAGE"
```

The Dockerfile pins the build tools and installs the released SDK. The final
image contains only Python, the virtual environment, and the worker source, and
runs as a non-root user. Until the plugin is released, update the standalone
`pyproject.toml` to a released or git-pinned SDK and regenerate `uv.lock`, as
noted at the top of this file and in the `Dockerfile`.

## 5. Render and deploy the worker pool

The manifest pins the Google-Built Collector image to `0.156.0`. It gives the
collector an HTTP startup probe and declares the worker's dependency on that
probe. The application also performs a bounded `localhost:4317` readiness wait
to protect deployments made through older Cloud Run tooling.

```bash
export INSTANCE_COUNT=1
export RENDERED_MANIFEST="/tmp/${WORKER_POOL}.yaml"

envsubst < gcp_cloud_run/worker-pool.yaml > "$RENDERED_MANIFEST"

gcloud run worker-pools replace "$RENDERED_MANIFEST" \
  --project "$PROJECT_ID"
```

The collector configuration is injected as the secret environment variable
`OTELCOL_CONFIG` and loaded with `--config=env:OTELCOL_CONFIG`. This is
intentional: secret-backed file volumes have been rejected by some Cloud Run
worker-pool rollouts even where current documentation advertises support.

The plugin supports overriding `metric_periodicity`, but the collector does not
batch cumulative metrics. It forwards each SDK export directly, including any
runtime shutdown-time export, so two points for one Managed Prometheus time
series cannot be grouped into the same request. Traces use a dedicated
five-second batch processor.

## 6. Start a Workflow

The local starter accepts either `TEMPORAL_API_KEY` or a file path. Prefer the
file path so the credential does not appear in shell history.

```bash
uv sync --group gcp-cloud-run

TEMPORAL_API_KEY_FILE="$TEMPORAL_API_KEY_FILE" \
  uv run --group gcp-cloud-run python -m gcp_cloud_run.starter
```

The expected result ends with:

```text
Hello, Temporal!
```

## 7. Verify telemetry

In the Cloud Run logs, verify that the worker reports the expected endpoint and
worker-pool-derived service name, without exporter errors:

```bash
gcloud run worker-pools logs read "$WORKER_POOL" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --limit 100
```

Then verify:

- Trace Explorer contains `RunWorkflow:GreetingWorkflow` with
  `service.name` equal to the worker-pool name.
- Metrics Explorer contains
  `prometheus.googleapis.com/temporal_workflow_completed_total/counter`.
- The trace and metrics have the expected Cloud Run, region, and project
  resource attributes added by the collector's GCP resource detector.

Trace indexing can lag successful OTLP export. Check collector error logs before
treating a temporarily absent Trace Explorer result as an export failure.

## 8. Scale to zero

Stop continuous compute charges immediately after validation:

```bash
gcloud run worker-pools update "$WORKER_POOL" \
  --instances 0 \
  --project "$PROJECT_ID" \
  --region "$REGION"
```

Cloud Run sends `SIGTERM` to both containers. The worker begins Temporal Worker
shutdown, allows up to five seconds for graceful completion, then force-flushes
Python traces with a two-second limit. A clean application shutdown logs
`traces_flushed=True`.

Temporal Core metrics are exported periodically and do not currently expose an
explicit flush operation. This is an accepted limitation: on scale-down, metric
samples accumulated since the last periodic export (up to one
`metric_periodicity` interval, 60 seconds by default) may not be delivered
before the process exits. Only the trailing, not-yet-exported window is
affected; earlier metrics are already in Google Managed Service for Prometheus.

## Troubleshooting

- **No Temporal spans:** Keep `add_temporal_spans=True`. The endpoint, service
  name, tracer provider, runtime, and Core metrics use GCP defaults, but named
  Temporal operation spans are intentionally opt-in.
- **Collector startup ordering is rejected:** Older worker-pool rollouts or CLI
  versions might not accept a startup probe plus container dependency. Remove
  only the `run.googleapis.com/container-dependencies` annotation; the worker's
  bounded readiness wait still prevents it from connecting before the
  collector listens.
- **`gcloud` reports a missing `grpc` Python module:** Prefer Cloud Shell or a
  current Google Cloud CLI installation. Some local installations require a
  Python environment containing `grpcio` together with
  `CLOUDSDK_PYTHON_SITEPACKAGES=1`; this is a CLI issue, not a worker setting.
- **Authentication says the JWT is missing:** Confirm the configured secret
  version contains only the Temporal API key. The sample strips the common
  trailing newline automatically.
