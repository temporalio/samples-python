# Survey Poll

A Temporal sample that collects responses to the survey question
**"Are you attending Replay 2026?"** with answers `Yes | No | Maybe`.

The sample has two modes that share the same code:

1. **Real app mode.** Each response is persisted to an S3 bucket (durable
   audit log) and signalled to a long-lived `PollAggregatorWorkflow` that
   maintains live counts. A FastAPI dashboard shows the live tally; a
   background task inside the UI backend polls the aggregator every **500 ms**
   via Temporal Query and caches the latest `TallyResult`. The browser
   fetches the cached value every 500 ms and redraws a bar chart. A **Reset
   Results** button signals the aggregator to zero its in-memory counters
   (the S3 audit log is preserved).
2. **Scaling-demo mode.** Setting `SURVEY_DURATION_SECONDS=150` makes each
   activity hold the local worker's single slot long enough to saturate,
   which provokes overflow Lambda invocations from the serverless worker
   (mirrors the `pi-worker` / `lambda_worker` demo pair).

## Architecture

```
  starter.py / load_starter.py
          │
          ▼
  SurveyResponseWorkflow (one per respondent)
          │
          ├─► execute_activity(record_response) ──► boto3 S3 PutObject
          │
          └─► signal(PollAggregatorWorkflow.submit_vote, response)

  PollAggregatorWorkflow (singleton on tq-survey-aggregator)
      @signal submit_vote → increments in-memory Counter
      @signal reset       → zeroes the Counter
      @query  tally       → returns TallyResult
      continue-as-new once history length > 5_000 events

  ui/app.py (FastAPI + uvicorn)
      background task   → queries aggregator every 500 ms, caches TallyResult
      GET /             → serves static dashboard
      GET /tally        → returns cached TallyResult + freshness metadata
      POST /reset       → signals PollAggregatorWorkflow.reset
```

Two task queues:

- `tq-survey-replay2026` — response workflows + `record_response` activity.
  Polled by both the local worker and the Lambda worker.
- `tq-survey-aggregator` — the aggregator only. Polled by the local worker.
  The Lambda worker does **not** poll this queue because the aggregator is
  long-lived and must not run in a function with a ~15-minute timeout. As a
  consequence, **the UI dashboard requires `worker.py` to be running
  locally** — if only the Lambda worker is up, the aggregator has no poller
  and `/tally` queries will time out.

## Files

| File | Description |
|------|-------------|
| `models.py` | `SurveyResponse` enum, `SurveyResponseInput` / `TallyResult` dataclasses, task-queue and workflow-ID constants |
| `workflows.py` | `SurveyResponseWorkflow`, `PollAggregatorWorkflow` (`submit_vote`, `reset`, `tally`) |
| `activities.py` | `record_response` activity — writes to S3, plus optional saturation loop |
| `s3_util.py` | `boto3.put_object` wrapper with hour-partitioned key layout |
| `worker.py` | Local worker; runs one `Worker` per task queue |
| `lambda_function.py` | AWS Lambda entry point (response workflow only) |
| `starter.py` | Fire a single vote |
| `load_starter.py` | Load generator (burst + ramp modes) with Yes/Maybe/No distribution |
| `start_aggregator.py` | One-shot starter for the aggregator workflow |
| `ui/app.py` | FastAPI backend; 500 ms background poller + `/tally`, `/reset` endpoints |
| `ui/static/index.html` | Single-page Chart.js dashboard (Replay dark theme, Reset button) |
| `deploy-lambda.sh` | Builds the Lambda zip (bundles `*.py` from this dir + temporalio + OTel) |
| `mk-iam-role.sh` | Creates the IAM role Temporal Cloud assumes to invoke the Lambda |
| `iam-role-for-temporal-lambda-invoke-test.yaml` | CloudFormation template used by `mk-iam-role.sh` |
| `pyproject.toml` | Project dependencies (temporalio, boto3[crt], fastapi, uvicorn) |
| `temporal.toml` | Temporal client connection configuration |

## Deployment identity

- Deployment name: `survey-replay2026`
- Build ID: `v3` (aggregator + S3 + UI)

## Prerequisites

- A [Temporal Cloud](https://temporal.io/cloud) namespace (or self-hosted cluster)
- mTLS client cert/key — place as `client.pem` / `client.key` and uncomment the
  TLS block in `temporal.toml`
- Python 3.10+
- [`mise`](https://mise.jdx.dev/) (for `uv`) — `mise.toml` in this directory
  pins the `uv` version. Run `mise install` once, then `mise exec -- uv sync`
  to install deps.
- AWS S3 bucket + AWS credentials resolvable by boto3 (env vars, shared
  config, SSO, or instance profile). If your `~/.aws/config` uses SSO or
  IAM Identity Center login, the `boto3[crt]` extras in `pyproject.toml`
  cover the required `awscrt` dependency; no extra action needed.

## Setup

### 1. Install dependencies

```bash
mise install          # installs uv
mise exec -- uv sync  # resolves Python deps into .venv
```

### 2. Configure Temporal connection

Edit `temporal.toml` with your namespace address and credentials.

### 3. Configure S3

```bash
export SURVEY_S3_BUCKET=my-survey-responses-bucket
# boto3 credentials via env, `aws configure`, SSO, etc.
```

Responses are keyed as
`survey-replay2026/responses/<YYYY>/<MM>/<DD>/<HH>/<user_id>.json`.
Same `user_id` → same key → idempotent re-writes.

### 4. Run the local worker

```bash
TEMPORAL_CONFIG_FILE=temporal.toml \
SURVEY_S3_BUCKET=my-survey-responses-bucket \
mise exec -- uv run python worker.py
```

The worker process runs two `Worker` instances in parallel — one for the
response queue and one for the aggregator queue.

### 5. Start the aggregator workflow

Either run the one-shot script (idempotent; no-op if already running):

```bash
TEMPORAL_CONFIG_FILE=temporal.toml mise exec -- uv run python start_aggregator.py
```

…or let the UI backend auto-start it on first boot (see next step).

### 6. Start the UI dashboard

```bash
TEMPORAL_CONFIG_FILE=temporal.toml \
mise exec -- uv run uvicorn ui.app:app --reload --port 8000
```

Open http://localhost:8000. The dashboard refreshes every 500 ms.

> **The UI requires `worker.py` from step 4 to be running.** The aggregator
> workflow is polled only by the local worker, not the Lambda worker
> (intentional — the aggregator is long-lived). If the local worker is down,
> `/tally` queries against the aggregator will time out and the cached
> tally in the UI backend will go stale. The "Last updated" text in the
> dashboard will turn amber to indicate this.

### 7. Fire votes

```bash
# Single vote
TEMPORAL_CONFIG_FILE=temporal.toml mise exec -- uv run python starter.py

# Many votes with Yes/Maybe/No distribution
TEMPORAL_CONFIG_FILE=temporal.toml mise exec -- uv run python load_starter.py \
    --mode burst --burst-size 100 --yes-pct 70 --maybe-pct 20 --no-pct 10
```

Each respondent is assigned a unique `user_id` (`user-<run_id>-<index>`).
Workflow IDs are `survey-replay2026-<user_id>`.

**About dedup.** The default `id_reuse_policy` (`ALLOW_DUPLICATE`) blocks a
second `start_workflow` with the same ID **only while the previous run is
still Running**. Once a vote workflow Completes, the same `user_id` can vote
again and the aggregator will increment twice. With
`SURVEY_DURATION_SECONDS=0` (the default in real-app mode) each vote
completes in milliseconds, so there is effectively no dedup window. If you
want strict one-vote-per-user across a run, pass
`id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE` on the
`start_workflow` call. In scaling-demo mode (`SURVEY_DURATION_SECONDS=150`)
the running window is long enough that duplicates are de facto rejected.

### 8. Reset results (optional)

Click the **Reset Results** button in the dashboard, or `POST /reset` the
backend directly. This signals the aggregator to zero its live Counter.
**The S3 audit log is intentionally preserved**; reset only clears the
dashboard tally. Existing `SurveyResponseWorkflow` runs are not terminated.

## Scaling-demo mode

The real-app path runs the activity to completion in milliseconds once the
S3 PUT returns. To reproduce the original scaling demo (local worker
saturation → Lambda scale-up), set `SURVEY_DURATION_SECONDS` on the worker:

```bash
SURVEY_DURATION_SECONDS=150 \
TEMPORAL_CONFIG_FILE=temporal.toml \
SURVEY_S3_BUCKET=my-survey-responses-bucket \
mise exec -- uv run python worker.py
```

Each activity now also runs a 150-second heartbeat loop on top of the S3
PUT. With `max_concurrent_activities=1`, a burst of 30 respondents
saturates the local worker and overflow drains via the Lambda worker (if
deployed). See the original notes in
[../pi-worker/README.md](../pi-worker/README.md) for background.

## Deploying the Lambda worker

```bash
./mk-iam-role.sh survey-replay2026-worker-role <external-id> <lambda-arn>
./deploy-lambda.sh survey-replay2026-worker
```

The `deploy-lambda.sh` in this directory bundles every `.py` the Lambda
needs (`lambda_function.py`, `workflows.py`, `activities.py`, `models.py`,
`s3_util.py`). If you copy a fresh one from `../lambda_worker/`, remember
to add the extra files to the `cp` line.

### Lambda S3 permissions

The Lambda's execution role needs `s3:PutObject` on the survey prefix or the
activity fails with `AccessDenied`. Attach this inline policy to the role
created by `mk-iam-role.sh` (swap the bucket name to yours):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SurveyPollWriteResponses",
      "Effect": "Allow",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::my-survey-responses-bucket/survey-replay2026/responses/*"
    }
  ]
}
```

```bash
aws iam put-role-policy \
  --role-name <role-name-from-mk-iam-role.sh> \
  --policy-name survey-s3-write \
  --policy-document file://survey-s3-write.json
```

If your bucket uses SSE-KMS encryption, also grant `kms:GenerateDataKey` +
`kms:Encrypt` on the CMK; otherwise PutObject still errors.

The Lambda only registers `SurveyResponseWorkflow` and `record_response`.
The aggregator is intentionally excluded — it's long-lived and belongs on
a durable host.

See `../lambda_worker/README.md` for the full Lambda setup including the
external ID flow and optional OpenTelemetry layer wiring.

## Continue-as-new

The aggregator workflow calls `continue_as_new` once its history length
exceeds ~5,000 events (≈ 2,500 votes). The new run is seeded with the
current `TallyResult` so counts survive the CAN boundary seamlessly. The
workflow ID stays constant; only the run ID changes.

## Aggregator reseeding (out of scope)

If you start the aggregator *after* votes already exist in S3, the
in-memory counts will start at zero. Replaying S3 into the aggregator is
left as a follow-up — a small admin workflow that LISTs the bucket and
sends synthetic `submit_vote` signals, or seeds a fresh run via
`start_workflow` with a backfilled `TallyResult`.

## Troubleshooting

- **`ResourceExhausted: consistent query buffer is full`** — the
  aggregator workflow is processing a backlog of signals and can't serve
  queries fast enough. Normally handled by the UI's cache + single
  background poller (see `ui/app.py`); if it still shows up, reduce
  `load_starter.py --burst-size` or raise `POLL_INTERVAL_SECONDS`.
- **`/tally` cache goes stale (amber timestamp) / `Tally poll failed:
  Timeout expired` in UI logs** — the aggregator has no polling worker.
  Check that `worker.py` is running and polling `tq-survey-aggregator` in
  the Temporal Cloud Workers view.
- **`Tally poll failed: MissingDependencyException: Using the login
  credential provider requires... botocore[crt]`** — your AWS credential
  chain walks through SSO / IAM Identity Center. Ensure `mise exec --
  uv sync` ran against the current `pyproject.toml` (which already pulls
  `boto3[crt]`).
- **Activity fails with `AccessDenied: ... is not authorized to perform:
  s3:PutObject`** — see the "Lambda S3 permissions" section above. Same
  applies to the local worker's AWS identity if running locally.
- **`Runtime.ImportModuleError: No module named '<something>'` on Lambda
  cold start** — the deploy bundle is missing a file. Check that the `cp`
  line in `deploy-lambda.sh` includes every `.py` this directory ships.