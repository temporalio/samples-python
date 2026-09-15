# Strands Agent on Bedrock AgentCore

This sample demonstrates how to run a [Strands Agents](https://strandsagents.com/) agent as a
Temporal Workflow, inside an [Amazon Bedrock AgentCore
Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime.html).

It combines three things:

- The [Temporal Strands
  plugin](https://docs.temporal.io/develop/python/integrations/strands-agents),
  which runs the agent inside a Workflow and turns every model call into a
  Temporal Activity -- so model invocations get durable retries, timeouts, and
  crash recovery.
- The [AgentCore Code
  Interpreter](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-getting-started.html)
  as the agent's tool, so it validates its answers by running Python in a managed
  sandbox instead of doing arithmetic in its head. The Temporal plugin enables wrapping the tool with an activity.
- [Temporal Serverless Workers](https://docs.temporal.io/serverless-workers) to launch the AgentCore Runtime when
workflows kick off.

## Prerequisites

- A [Temporal Cloud](https://temporal.io/cloud) namespace (or a self-hosted
  Temporal cluster reachable from AgentCore)
- Python 3.10+ and [uv](https://docs.astral.sh/uv/)
- Node.js 20+ -- the [AgentCore CLI](https://github.com/aws/agentcore-cli) is an
  npm package: `npm install -g @aws/agentcore`
- AWS CLI configured, and the [AWS
  CDK](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html) bootstrapped
  in the target account/region (`cdk bootstrap`)
- AWS permissions for the AgentCore CLI (S3, IAM, CloudFormation): see [Use the
  AgentCore
  CLI](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html#runtime-permissions-cli)
- Access to the Amazon Nova Lite model in your target Region. The sample uses
  the model ID `amazon.nova-lite-v1:0`.


Docker is not needed. With the CodeZip build there is no image: the CLI uploads a
zip of this directory and the platform runs it on a managed Python runtime, which
also takes care of AgentCore's ARM64 (Graviton) requirement.

## Files

| File | Description |
|------|-------------|
| `agentcore_worker.py` | Runtime entry point -- a `BedrockAgentCoreApp` that runs the Worker |
| `workflows.py` | `StrandsAgentWorkflow` -- a `TemporalAgent` with the code interpreter tool |
| `activities.py` | `execute_code` -- the AgentCore Code Interpreter, wrapped as a Temporal Activity |
| `starter.py` | Helper program to start a Workflow execution from a local machine |
| `agentcore/agentcore.json` | AgentCore project config -- the runtime definition (entry point, env vars, lifecycle) |
| `agentcore/aws-targets.json` | AWS account and region to deploy into |
| `bin/mk-invoke-role.sh` | Creates the role Temporal Cloud assumes to invoke the runtime |
| `iam-role-for-temporal-agentcore-invoke.yaml` | CloudFormation template for that role |
| `code-interpreter-policy.json` | Code Interpreter permissions, attached to the runtime's execution role via `additionalPolicies` |
| `bin/create-runtime.sh` | Creates/updates the runtime with the AgentCore CLI |


## Determining Busy vs Idle

AgentCore has two levers to control timeouts: idle and max. The idle timeout allows the runtime to exit early when there
is no more work for it to do. The max timeout determines the max amount of time a session is allowed to run. A naive
approach would be to have the Temporal worker spin up and never shutdown on its own. However, the max timeout doesn't
offer graceful shutdown and it would defeat the purpose of AgentCore's idle timer.

This sample, includes a ActivityTracker which intercepts the Worker activity and keeps the worker alive. If the worker sits
idle for AGENTCORE_DEBOUNCE_SECONDS, it will shutdown and enable AgentCore to exit based on idle timer. The idle timer
in this configuration can be very short since there is no temporal worker running when idle.

## Setup

This sample opts to utilize the new AgentCore CLI for creating and updating both the Runtime and Runtime Endpoint.

### 1. Choose the AWS account and region

Edit `agentcore/aws-targets.json` with the account ID and region to deploy into. AgentCore is only available in
[certain regions](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-regions.html), and the Region
must support Amazon Nova Lite.

### 2. Configure the Temporal connection

The Worker reads its connection details from the runtime's environment, so edit
the `envVars` on the runtime in `agentcore/agentcore.json`:

| Variable | Description |
|----------|-------------|
| `TEMPORAL_ADDRESS` | Namespace endpoint, e.g. `<ns>.<account>.tmprl.cloud:7233` |
| `TEMPORAL_NAMESPACE` | Namespace, e.g. `<ns>.<account>` |
| `TEMPORAL_API_KEY` | Temporal Cloud API key (TLS is enabled automatically when set) |
| `TEMPORAL_TASK_QUEUE` | Task Queue to poll (defaults to `workflows.TASK_QUEUE`) |
| `TEMPORAL_DEPLOYMENT_NAME` / `TEMPORAL_BUILD_ID` | **Required.** Worker Deployment name and Build ID. The Worker always registers a Worker Deployment Version, and refuses to start without these -- a defaulted build ID would silently strand Workflows on a version nothing is polling |
| `AWS_REGION` | Region for the agent's Bedrock model calls and its Code Interpreter sessions |
| `CODE_INTERPRETER_IDENTIFIER` | Optional; overrides the default `aws.codeinterpreter.v1` sandbox |
| `AGENTCORE_DEBOUNCE_SECONDS` | How long the Worker keeps polling after it goes idle (default `60`) |

Putting the API key in `envVars` keeps this sample short. For production, read it
from secret store in `agentcore_worker.py` instead of shipping it in the
runtime config.

### 3. Create the runtime and its endpoint

```bash
./bin/create-runtime.sh
```

This validates the config, zips this directory, uploads it, and deploys the runtime through CDK. Re-run it to roll out
changes. (`.git`, `.venv`, `__pycache__` and `node_modules` are excluded from the zip.)

`agentcore deploy` also creates the runtime's execution role, so there is nothing to configure for it. The one thing
that role does not grant by default is Code Interpreter access, which this sample needs, so `agentcore.json` points at a
policy file that is attached to it:

```json
"additionalPolicies": ["code-interpreter-policy.json"]
```

It also creates the **runtime endpoint** that Temporal Cloud invokes. The endpoint is declared alongside the runtime in
`agentcore/agentcore.json`. You can find the Endpoint ARN in the CloudFormation Stack Output displayed after running
`create-runtime.sh` or found in the AWS Console.


On the first run this step also generates `agentcore/cdk/`, the CDK app that `agentcore deploy` synthesizes. That
scaffold is generated boilerplate -- it reads `agentcore.json` and `aws-targets.json` at synth time and holds nothing
specific to this sample -- so it is gitignored rather than checked in.

### 4. Create the Temporal Cloud invoke role

With Serverless Workers, Temporal Cloud assumes a role in your account and calls the endpoint when Tasks arrive. Create
that role with the same External ID used to create your serverless worker configuration:

```bash
./bin/mk-invoke-role.sh <stack-name> <external-id> <agent-runtime-arn>
```

That deploys `iam-role-for-temporal-agentcore-invoke.yaml`, which grants `bedrock-agentcore:InvokeAgentRuntime` and
`bedrock-agentcore:GetAgentRuntimeEndpoint`, and trusts Temporal Cloud's principals only under your External ID. Pass
the runtime ARN with a trailing `*` (`...:runtime/temporal_strands_worker-XXXXXXXXXX*`) so the role covers the runtime
*and* its endpoints. Give the stack's `RoleARN` output, and the endpoint, back to Temporal Cloud.

### 5. Set up the Worker Deployment Version

The Worker always registers the Worker Deployment Version named by
`TEMPORAL_DEPLOYMENT_NAME` / `TEMPORAL_BUILD_ID`, and pins Workflows to it. You
must set that version as current, or nothing will be routed to the Worker:

```bash
temporal worker deployment create \
    --name <TEMPORAL_DEPLOYMENT_NAME>

temporal worker deployment create-version  \
      --aws-agentcore-endpoint-arn <RuntimeEndpointARN> \
      --aws-agentcore-assume-role-external-id <ExternalId> \
      --aws-agentcore-assume-role-arn <InvokeRoleArn> \
      --build-id <TEMPORAL_BUILD_ID> \
      --deployment-name <TEMPORAL_DEPLOYMENT_NAME>
```

See [Worker
deployments](https://docs.temporal.io/production-deployment/worker-deployments).

### 6. Run the agent

`starter.py` reads the same connection variables the Worker uses, so export
them and run it from this directory:

```bash
export TEMPORAL_ADDRESS=<your-namespace>.<account>.tmprl.cloud:7233
export TEMPORAL_NAMESPACE=<your-namespace>.<account>
export TEMPORAL_API_KEY=<your-api-key>
```

```bash
uv run python starter.py
uv run python starter.py "Calculate the first 10 Fibonacci numbers."
```

Nothing else is needed: Temporal Cloud sees the Tasks on the Task Queue, invokes
the runtime endpoint, the Worker starts inside AgentCore, drains the queue, and
shuts itself down once idle.

The invocation itself returns straight away with `{"message": "worker starting"}`
rather than being held open for the whole polling window. The Worker runs as an
[async
task](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-long-run.html):
`add_async_task` keeps `/ping` on `HealthyBusy`, which is what keeps the AgentCore
session alive past its idle timeout, and `complete_async_task` releases it once
the Worker has drained. An invocation that arrives while a Worker is already
polling is acknowledged with `"worker already polling"` instead of starting a
second one.

Each Workflow execution gets its own sandbox, named after its Workflow ID.

The default prompt asks the agent to verify a claim by running code, so you
should see it open a sandbox and execute Python. In the Workflow history that
shows up as alternating `invoke_model` and `execute_code` Activities:

```bash
temporal workflow show --workflow-id agentcore-strands-workflow-id-1
```

Follow the Worker from the AgentCore side with `agentcore logs --runtime temporal_strands_worker`.
