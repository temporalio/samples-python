# Google Cloud Run Id

Run a Temporal Worker in a [Google Cloud Run worker
pool](https://cloud.google.com/run/docs/worker-pools) and derive its identity
from Cloud Run instance metadata with
[`temporalio.contrib.gcp.cloud_run.id`](https://python.temporal.io/temporalio.contrib.gcp.cloud_run.id.html)'s
`CloudRunIdPlugin`. Registered on the client, the plugin sets the identity to
`<instance_id>@<revision>` at connect time and propagates it to the worker, so
each running container is individually identifiable as a poller.

`CloudRunIdPlugin` is unreleased, so `pyproject.toml` pins `temporalio` to the
SDK commit that adds it (a git source, which also builds inside the container);
drop the `[tool.uv.sources]` override once it ships on PyPI.

Configure the worker and starter with `TEMPORAL_TASK_QUEUE` (required),
`TEMPORAL_ADDRESS` (default `localhost:7233`), `TEMPORAL_NAMESPACE` (default
`default`), and `TEMPORAL_API_KEY` (set for Temporal Cloud; enables TLS).
Cloud Run sets `CLOUD_RUN_WORKER_POOL` and `CLOUD_RUN_REVISION` automatically.
Worker pools bill while running, so scale to zero (step 4) after testing.

## 1. Deploy the worker pool

Cloud Build builds the image from the `Dockerfile` and starts one instance:

```bash
gcloud run worker-pools deploy temporal-worker --source . --region us-central1 \
  --set-env-vars TEMPORAL_ADDRESS=your-namespace.account-id.tmprl.cloud:7233,TEMPORAL_NAMESPACE=your-namespace.account-id,TEMPORAL_TASK_QUEUE=gcp-cloud-run \
  --set-secrets TEMPORAL_API_KEY=temporal-api-key:latest
```

Omit `--set-secrets` for a plaintext self-hosted server.

## 2. Confirm the worker registered

The startup log reports the derived identity `<instance_id>@<revision>`:

```bash
gcloud run worker-pools logs read temporal-worker --region us-central1 --limit 50
```

## 3. Start a Workflow

Run the starter locally from the repository root, against the same service and
task queue:

```bash
TEMPORAL_ADDRESS=your-namespace.account-id.tmprl.cloud:7233 \
TEMPORAL_NAMESPACE=your-namespace.account-id \
TEMPORAL_TASK_QUEUE=gcp-cloud-run \
TEMPORAL_API_KEY="$(cat /secure/path/to/temporal-api-key)" \
  uv run python -m gcp.cloud_run.id.starter
```

It prints `Workflow result: Hello, Cloud Run worker pool!`.

## 4. Scale to zero

```bash
gcloud run worker-pools update temporal-worker --instances 0 --region us-central1
```

Cloud Run sends `SIGTERM` and the worker shuts down gracefully.
