# Pi Worker

A companion to the [`lambda_worker`](../lambda_worker) sample. It runs the **same**
`SampleWorkflow` and `hello_activity`, but as a normal long-running Temporal worker
process instead of an AWS Lambda function.

Both workers register under the same Worker Deployment (`demo-order`) with the same
Build ID (`v1`) and poll the same task queue (`tq-demo-order`). From Temporal's point of
view they are interchangeable members of that deployment version — tasks for the
workflow can be dispatched to either the Lambda-based worker or this plain worker.

## Files

| File | Description |
|------|-------------|
| `worker.py` | Entry point that starts a normal `Worker` with `WorkerDeploymentConfig` matching the lambda_worker |
| `workflows.py` | Same `SampleWorkflow` as the lambda_worker sample |
| `activities.py` | Same `hello_activity` as the lambda_worker sample |
| `starter.py` | Helper program to start a workflow execution |
| `temporal.toml` | Temporal client connection configuration (update with your namespace) |

## Deployment identity

The worker registers as:

- Deployment name: `demo-order`
- Build ID: `v1`
- Task queue: `tq-demo-order`

These values match the `lambda_worker` sample's `lambda_function.py`, so both workers
belong to the same deployment version.

## Prerequisites

- A [Temporal Cloud](https://temporal.io/cloud) namespace (or a self-hosted Temporal
  cluster)
- mTLS client certificate and key for your Temporal namespace if required (place as
  `client.pem` / `client.key` in this directory and uncomment the TLS block in
  `temporal.toml`)
- Python 3.10+

## Setup

### 1. Configure Temporal connection

Edit `temporal.toml` with your Temporal Cloud namespace address and credentials.

### 2. Run the worker

From inside this directory:

```bash
TEMPORAL_CONFIG_FILE=temporal.toml uv run python worker.py
```

### 3. Start a workflow

In another terminal, from this directory:

```bash
TEMPORAL_CONFIG_FILE=temporal.toml uv run python starter.py
```

The workflow will be executed by whichever worker in the `demo-order / v1` deployment
version picks up the task — this pi-worker, the lambda_worker, or both across tasks.
