# Google Cloud Run Worker Identity

This sample runs a long-lived Temporal Worker in a [Google Cloud Run worker
pool](https://cloud.google.com/run/docs/worker-pools) and uses the
[`temporalio.contrib.gcp.cloud_run.worker_id`](https://python.temporal.io/temporalio.contrib.gcp.cloud_run.worker_id.html)
`WorkerIDPlugin` to derive the worker's identity and its Worker Deployment
version from Cloud Run instance metadata.

Cloud Run runs a long-lived container rather than a per-invocation handler, so
this is a small metadata-driven plugin -- not a worker wrapper. The worker
registers `WorkerIDPlugin()` on the client via `Client.connect(plugins=[...])`.
At connect time the plugin:

- reads the deployment name from `CLOUD_RUN_WORKER_POOL` (worker pools), falling
  back to `K_SERVICE` (services);
- reads the revision from `CLOUD_RUN_REVISION`, falling back to `K_REVISION`;
- fetches this container's unique instance id from the Cloud Run metadata server.

From that it sets the client `identity` to `<instance_id>@<revision>` (unless you
passed one) and configures the worker with a `WorkerDeploymentConfig` (deployment
name = worker-pool name, build id = revision) with Worker Versioning enabled and
a **PINNED** default versioning behavior. Client plugins propagate to workers
automatically, so there is nothing to wire up on the `Worker`. The sample
registers a simple greeting Workflow and Activity, but the pattern applies to any
Workflow/Activity definitions.

> **Worker pools vs. services.** A Cloud Run *worker pool* has no HTTP endpoint;
> it is designed for long-running background workloads such as a Temporal
> Worker, which is why it is the primary target here. Worker pools use manual
> scaling and active instances are billed continuously, so remember to scale to
> zero after testing.

> **This helper is not released yet.** `pyproject.toml` pins `temporalio` to a
> local path source (`../../sdk-python-2`) so the sample can be run and
> type-checked locally. Drop that `[tool.uv.sources]` override once an SDK
> release that includes the helper is on PyPI. The local path is not available
> inside a Docker build context, so the container build must use a released or
> git-pinned `temporalio`; see the `Dockerfile`.

## Files

| File | Description |
|------|-------------|
| `worker.py` | Long-lived worker: registers `WorkerIDPlugin` to set identity + deployment version from Cloud Run metadata, then runs until SIGTERM |
| `workflows.py` | Sample Workflow that executes a greeting Activity (PINNED versioning behavior) |
| `activities.py` | Sample Activity that returns a greeting string |
| `settings.py` | Reads `TEMPORAL_*` connection settings from the environment |
| `starter.py` | Helper program to start a Workflow execution from a local machine |
| `Dockerfile` | Builds the worker container image |
| `.dockerignore` | Limits the Docker build context to the worker sources |
| `pyproject.toml` | Standalone dependencies for the sample |

## Prerequisites

- A [Temporal Cloud](https://temporal.io/cloud) namespace, or a self-hosted
  Temporal cluster reachable from Cloud Run (a plaintext connection is fine).
- A Google Cloud project with billing enabled and the Google Cloud CLI
  (`gcloud`) authenticated to it.
- Permission to manage Cloud Run worker pools and Cloud Build.
- Python 3.10+ and [`uv`](https://docs.astral.sh/uv/) to run the starter
  locally.

## Configuration

The worker and starter read the same environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TEMPORAL_TASK_QUEUE` | yes | -- | Task queue the worker polls and the starter targets |
| `TEMPORAL_ADDRESS` | no | `localhost:7233` | Temporal frontend address |
| `TEMPORAL_NAMESPACE` | no | `default` | Temporal namespace |
| `TEMPORAL_API_KEY` | no | -- | Set for Temporal Cloud; presence enables TLS |

## 1. Deploy the worker pool

Deploy from source; Cloud Build builds the image from the `Dockerfile` and Cloud
Run starts one instance:

```bash
gcloud run worker-pools deploy temporal-worker \
  --source . \
  --region us-central1 \
  --set-env-vars TEMPORAL_ADDRESS=your-namespace.account-id.tmprl.cloud:7233,TEMPORAL_NAMESPACE=your-namespace.account-id,TEMPORAL_TASK_QUEUE=gcp-cloud-run
```

For a self-hosted plaintext server, set `TEMPORAL_ADDRESS` to its
`host:7233` and omit any API key. For Temporal Cloud, provide the API key as a
secret rather than a plaintext env var, for example:

```bash
gcloud run worker-pools deploy temporal-worker \
  --source . \
  --region us-central1 \
  --set-env-vars TEMPORAL_ADDRESS=your-namespace.account-id.tmprl.cloud:7233,TEMPORAL_NAMESPACE=your-namespace.account-id,TEMPORAL_TASK_QUEUE=gcp-cloud-run \
  --set-secrets TEMPORAL_API_KEY=temporal-api-key:latest
```

Cloud Run sets `CLOUD_RUN_WORKER_POOL` and `CLOUD_RUN_REVISION` in the
container, which the helper reads automatically -- you do not set them yourself.

## 2. Confirm the worker registered

Check the worker-pool logs for the startup line, which reports the derived
identity, deployment, and build id:

```bash
gcloud run worker-pools logs read temporal-worker --region us-central1 --limit 50
```

You can also confirm the poller identity `<instance_id>@<revision>` with the
Temporal CLI:

```bash
temporal task-queue describe --task-queue gcp-cloud-run
```

## 3. Start a Workflow

Run the starter locally against the same Temporal service and task queue:

```bash
TEMPORAL_ADDRESS=your-namespace.account-id.tmprl.cloud:7233 \
TEMPORAL_NAMESPACE=your-namespace.account-id \
TEMPORAL_TASK_QUEUE=gcp-cloud-run \
TEMPORAL_API_KEY="$(cat /secure/path/to/temporal-api-key)" \
  uv run python starter.py
```

The expected output ends with:

```text
Workflow result: Hello, Cloud Run worker pool!
```

## 4. Scale to zero

Worker-pool instances are billed while running, so scale to zero when finished:

```bash
gcloud run worker-pools update temporal-worker --instances 0 --region us-central1
```

Cloud Run sends `SIGTERM`, and the worker begins a graceful Temporal Worker
shutdown before the process exits.
