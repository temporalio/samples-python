# OpenAI Agents SDK Agent on Bedrock AgentCore

This sample demonstrates how to run an [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/) agent as a
Temporal Workflow, inside an [Amazon Bedrock AgentCore
Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime.html).

It combines three things:

- The [Temporal OpenAI Agents
  plugin](https://docs.temporal.io/develop/python/integrations/openai-agents-sdk),
  installed as the standalone `temporalio-openai-agents` package (requires Temporal 1.34.0 or later),
  which runs the agent inside a Workflow and turns every model call into a
  Temporal Activity -- so model invocations get durable retries, timeouts, and
  crash recovery.
- The [AgentCore Code
  Interpreter](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-getting-started.html)
  as the agent's tool, so it validates its answers by running Python in a managed
  sandbox instead of doing arithmetic in its head. The Temporal plugin enables wrapping the tool with an activity.
- [Temporal Serverless Workers](https://docs.temporal.io/serverless-workers) to launch the AgentCore Runtime when
workflows kick off.
- **Activity sessions (experimental)**, so the agent's model calls and `execute_code` run on the same AgentCore microVM
  that holds the Workflow -- see [Activity sessions](#activity-sessions-experimental).

> **Temporary: unreleased dependencies.** Activity sessions are not in a released `temporalio` yet, and
> `OpenAIAgentsPlugin(session_options=...)` is not in a released `temporalio-openai-agents`. Until they are,
> `pyproject.toml` resolves both from local wheels in `../wheels/`, built by
> [`../build-local-wheels.sh`](../build-local-wheels.sh), which clones `temporalio/sdk-python` (`dev/sticky-activities`)
> and `temporalio/ai-integrations` (`feature/activity-sessions`) from GitHub and builds from those clones. Run it
> before `uv sync` and before `bin/create-runtime.sh` -- see [Build the local wheels](#0-build-the-local-wheels-temporary).

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
- A Temporal Service with **sticky activity execution enabled** (activity sessions are experimental and need
  server support)
- For `../build-local-wheels.sh` (temporary, see above): git, uv, and Docker able to run `linux/arm64` containers
  (native on Apple silicon; QEMU/binfmt emulation on x86_64, which is much slower). A Rust toolchain is only needed
  for the optional macOS `temporalio` wheel (local `uv sync`, lint and tests on macOS); deploying does not need it.
  The script provides its own `protoc` for that wheel; set `PROTOC` to use a different one.
- An [OpenAI API key](https://platform.openai.com/api-keys) -- the agent calls the OpenAI API with the Agents SDK's
  default model (set `OPENAI_DEFAULT_MODEL` on the runtime to choose another)


The deploy itself needs no Docker. With the CodeZip build there is no image: the CLI installs the dependencies for
Linux ARM64 (Graviton) with your local `uv`, zips them with this directory, and the platform runs it on a managed
Python runtime. That local install is why the unreleased `temporalio` must exist as a Linux aarch64 wheel in
`../wheels/`.

## Files

| File | Description |
|------|-------------|
| `agentcore_worker.py` | Runtime entry point -- a `BedrockAgentCoreApp` that runs the Worker |
| `workflows.py` | `OpenAIAgentWorkflow` -- an Agents SDK `Agent` with the code interpreter tool, run with `Runner.run` |
| `activities.py` | `execute_code` -- the AgentCore Code Interpreter (via the `bedrock_agentcore` SDK client), wrapped as a Temporal Activity |
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

This sample includes a WorkTracker which counts in-flight Workflow and Nexus tasks (via a tracking slot supplier) and Activities (via an interceptor), and keeps the worker alive while any are running. If the worker sits
idle for AGENTCORE_DEBOUNCE_SECONDS, it will shutdown and enable AgentCore to exit based on idle timer. The idle timer
in this configuration can be very short since there is no temporal worker running when idle.

## Activity sessions (experimental)

By default, Temporal may dispatch a Workflow's Activities to any Worker polling the Task Queue. Here the Worker is
built so that every Activity the agent Workflow starts -- each model call and each `execute_code` -- runs on the
**same Worker, and so the same AgentCore microVM, that holds the Workflow**:

- `OpenAIAgentsPlugin(model_params=ModelActivityParameters(...), session_options=ActivitySessionOptions(placement=UseWorkflowSession()))` fills the session on every
  Activity the Workflow starts on its own Task Queue (a `workflow.activity_session(...)` scope in your code wins).
- The Worker passes `session_config=WorkerSessionConfig(admission=SingleSessionAdmission(stable_identity=session_id))`,
  keyed on the AgentCore runtime session (`context.session_id` in the entrypoint). The Worker then serves exactly one
  Workflow for its lifetime. Without a session id (e.g. a local run) it falls back to `WorkerSessionConfig()`.
- The plugin refuses to start a Worker that has no `session_config`. It is registered on the Client, which works because
  `Worker(...)` merges its own arguments (including `session_config`) before any plugin's `configure_worker` runs.
- Session Workers need fixed-size activity slots: the tuner uses a `FixedSizeSlotSupplier` for activities that matches the sync-Activity thread pool.
- `starter.py` keeps a plain `OpenAIAgentsPlugin()`; the Client only needs the plugin's data converter.

This requires a Temporal Service with sticky activity execution enabled.

## Setup

### 0. Build the local wheels (temporary)

```bash
../build-local-wheels.sh
uv lock --refresh && uv sync   # needs the macOS temporalio wheel when run on macOS
```

By default the script clones the sources from GitHub into the gitignored `../.wheel-build/` (re-runs fetch and reuse
the clones) and writes these to the gitignored `../wheels/`:

- `temporalio-1.34.0+sessions-…-manylinux2014_aarch64…whl`, built in Docker -- what the deploy installs
- `temporalio-1.34.0+sessions-…-macosx_11_0_arm64.whl`, only on macOS with Rust (`cargo`) installed; otherwise
  skipped with a message
- `temporalio_strands_agents-0.0.0-py3-none-any.whl` and `temporalio_openai_agents-0.0.0-py3-none-any.whl`
- `BUILD_INFO`: each repo URL, the requested ref and the resolved commit SHA, plus wheel checksums. Include it when
  reporting results.

Environment overrides:

| Variable | Default |
|----------|---------|
| `SDK_PYTHON_REPO` / `SDK_PYTHON_REF` | `https://github.com/temporalio/sdk-python.git` / `dev/sticky-activities` |
| `AI_INTEGRATIONS_REPO` / `AI_INTEGRATIONS_REF` | `https://github.com/temporalio/ai-integrations.git` / `feature/activity-sessions` |
| `SDK_CORE_REPO` | unset (the URL in sdk-python's `.gitmodules`, `temporalio/sdk-rust`); set when the sdk-core commit sdk-python pins lives in another repo or fork |
| `SDK_PYTHON_DIR` / `AI_INTEGRATIONS_DIR` | unset; set to a local checkout to build from it instead of cloning |
| `SKIP_LINUX` / `SKIP_MACOS` / `SKIP_PLUGINS` | unset; `1` skips that part |
| `RELOCK` | unset; `1` runs `uv lock --refresh` in both samples afterwards |
| `MANYLINUX_IMAGE` | `quay.io/pypa/manylinux2014_aarch64` |
| `PROTOC` | unset (uses `protoc-wheel-0` in a cached venv under `.wheel-build/`); set to a `protoc` binary for the macOS wheel |

A ref can be a branch, tag or commit SHA, e.g. to pin exact commits:

```bash
SDK_PYTHON_REF=e73f54d3 AI_INTEGRATIONS_REF=5492934 ../build-local-wheels.sh
```

The committed `uv.lock` records the hashes of the author's wheels, so re-lock after every build (`uv lock --refresh`
or `RELOCK=1`). The lock covers macOS and Linux, so locking needs both `temporalio` wheels. The deploy does not read
`uv.lock` -- it installs from `pyproject.toml` and only needs the Linux wheel and the plugin wheels.

#### Handing this sample to a tester

Prerequisites: git, uv, Docker with `linux/arm64` support, plus the deploy prerequisites above (Rust optional).

```bash
git clone -b feature/activity-sessions https://github.com/temporalio/samples-python.git
cd samples-python/bedrock_agentcore/openai_agent
../build-local-wheels.sh            # clone + build; prints wheels/BUILD_INFO
uv lock --refresh && uv sync        # optional: local runs/tests; needs the macOS wheel (macOS + Rust)
# then follow steps 1-6 below; step 3 (bin/create-runtime.sh) deploys
```

This sample opts to utilize the new AgentCore CLI for creating and updating both the Runtime and Runtime Endpoint.

### 1. Choose the AWS account and region

Edit `agentcore/aws-targets.json` with the account ID and region to deploy into. AgentCore is only available in
[certain regions](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-regions.html), and the region
needs AgentCore Code Interpreter available.

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
| `OPENAI_API_KEY` | **Required.** OpenAI API key for the agent's model calls |
| `OPENAI_DEFAULT_MODEL` | Optional; the OpenAI model for the agent (defaults to the Agents SDK's default model) |
| `AWS_REGION` | Region for the agent's Code Interpreter sessions |
| `CODE_INTERPRETER_IDENTIFIER` | Optional; overrides the default `aws.codeinterpreter.v1` sandbox |
| `AGENTCORE_DEBOUNCE_SECONDS` | How long the Worker keeps polling after it goes idle (default `60`) |

Putting the API keys in `envVars` keeps this sample short. For production, read it
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
the runtime ARN with a trailing `*` (`...:runtime/temporal_openai_worker-XXXXXXXXXX*`) so the role covers the runtime
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

Each Workflow execution gets its own sandbox, named after its Workflow ID. `execute_code` keeps the
`CodeInterpreter` client for that name in-process (activity sessions put every call on the same Worker), and a
fresh process finds the sandbox again by listing `READY` sessions with that name before starting a new one.

The default prompt asks the agent to verify a claim by running code, so you
should see it open a sandbox and execute Python. In the Workflow history that
shows up as alternating `invoke_model_activity` and `execute_code` Activities:

```bash
temporal workflow show --workflow-id agentcore-openai-workflow-id-1
```

Follow the Worker from the AgentCore side with `agentcore logs --runtime temporal_openai_worker`.
