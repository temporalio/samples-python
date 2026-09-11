## Caller pattern

The handler worker starts a `GreetingWorkflow` for a User ID.
`NexusGreetingServiceHandler` derives the Workflow ID and routes every Nexus operation to it.
The caller's input does not have that Workflow ID as the caller doesn't know it -- but the caller
sends in the User ID, and `NexusGreetingServiceHandler` knows how to get the desired Workflow ID
from that User ID (see the `get_workflow_id` call).

The handler worker uses the same `get_workflow_id` call to generate a Workflow ID from a User ID
when it launches the Workflow.

The caller Workflow:
1. Queries for supported languages (`get_languages` -- backed by a `@workflow.query`)
2. Changes the language to Arabic (`set_language` -- backed by a `@workflow.update` that calls an activity)
3. Confirms the change via a second query (`get_language`)
4. Approves the Workflow (`approve` -- backed by a `@workflow.signal`)

### Running

This sample requires a Temporal dev server build that supports Workflow Update callbacks. Download the compatible
binary from the [Temporal CLI pre-release instructions](https://docs.temporal.io/standalone-nexus-operation#temporal-cli-support).

Start the Temporal dev server with the required namespaces pre-created and Workflow Update callbacks enabled:

```bash
./temporal server start-dev \
  --dynamic-config-value history.enableUpdateCallbacks=true \
  --dynamic-config-value history.enableCHASMSignalBacklinks=true \
  --namespace nexus-messaging-handler-namespace \
  --namespace nexus-messaging-caller-namespace
```

Create the Nexus endpoint:

```bash
./temporal operator nexus endpoint create \
  --name nexus-messaging-nexus-endpoint \
  --target-namespace nexus-messaging-handler-namespace \
  --target-task-queue nexus-messaging-handler-task-queue
```

In one terminal, start the handler worker:

```bash
uv run python -m nexus_messaging.callerpattern.handler.worker
```

In another terminal, run the following command to start the example:

```bash
uv run python -m nexus_messaging.callerpattern.caller.app
```

Expected output:

```
Supported languages: [<Language.CHINESE: 2>, <Language.ENGLISH: 3>]
Language changed: ENGLISH -> ARABIC
Workflow approved
```
