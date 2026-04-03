# Lambda Worker

This sample demonstrates how to run a Temporal Worker inside an AWS Lambda function using
the [`lambda_worker`](https://python.temporal.io/temporalio.contrib.aws.lambda_worker.html)
contrib package. It includes optional OpenTelemetry instrumentation that exports traces
and metrics through AWS Distro for OpenTelemetry (ADOT).

The sample registers a simple greeting Workflow and Activity, but the pattern applies to
any Workflow/Activity definitions.

## Prerequisites

- A [Temporal Cloud](https://temporal.io/cloud) namespace (or a self-hosted Temporal
  cluster accessible from your Lambda)
- AWS CLI configured with permissions to create Lambda functions, IAM roles, and
  CloudFormation stacks
- mTLS client certificate and key for your Temporal namespace (place as `client.pem` and
  `client.key` in this directory)
- Python 3.10+

## Files

| File | Description |
|------|-------------|
| `lambda_function.py` | Lambda entry point -- configures the worker, registers Workflows/Activities, and exports the handler |
| `workflows.py` | Sample Workflow that executes a greeting Activity |
| `activities.py` | Sample Activity that returns a greeting string |
| `starter.py` | Helper program to start a Workflow execution from a local machine |
| `temporal.toml` | Temporal client connection configuration (update with your namespace) |
| `otel-collector-config.yaml` | OpenTelemetry Collector sidecar configuration for ADOT |
| `deploy-lambda.sh` | Packages and deploys the Lambda function |
| `mk-iam-role.sh` | Creates the IAM role that allows Temporal Cloud to invoke the Lambda |
| `iam-role-for-temporal-lambda-invoke-test.yaml` | CloudFormation template for the IAM role |
| `extra-setup-steps` | Additional IAM and Lambda configuration for OpenTelemetry support |

## Setup

### 1. Configure Temporal connection

Edit `temporal.toml` with your Temporal Cloud namespace address and credentials. In production,
we'd recommend reading your credentials from a secret store, but to keep this example simple
the toml file defaults to reading them from keys bundled along with the Lambda code.

### 2. Create the IAM role

This creates the IAM role that Temporal Cloud assumes to invoke your Lambda function:

```bash
./mk-iam-role.sh <stack-name> <external-id> <lambda-arn>
```

The External ID is provided by Temporal Cloud in your namespace's serverless worker
configuration.

### 3. (Optional) Enable OpenTelemetry

If you want traces, metrics, and logs, you'll have to attach the ADOT layet to your Lambda function.
You will need to add the appropriate layer for your runtime and region. See [this page
](https://aws-otel.github.io/docs/getting-started/lambda#getting-started-with-aws-lambda-layers)
for more info.

Then run the extra setup to grant the Lambda role the necessary permissions:

```bash
./extra-setup-steps <role-name> <function-name> <region> <account-id>
```

Update `otel-collector-config.yaml` with your function name and region as needed.

### 4. Deploy the Lambda function

```bash
./deploy-lambda.sh <function-name>
```

This installs Python dependencies, bundles them with your code and configuration files,
and uploads to AWS Lambda.

### 5. Start a Workflow

Use the starter program to execute a Workflow on the Lambda worker, using
the same config file the Lambda uses for connecting to the server:

```bash
TEMPORAL_CONFIG_FILE=temporal.toml uv run python lambda_worker/starter.py
```
