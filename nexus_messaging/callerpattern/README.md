## Caller pattern

The handler worker starts a `GreetingWorkflow` for a user ID.
`NexusGreetingServiceHandler` holds that ID and routes every Nexus operation to it.
The caller's input does not have that workflow ID as the caller doesn't know it -- but the caller
sends in the User ID, and `NexusGreetingServiceHandler` knows how to get the desired workflow ID
from that User ID (see the `get_workflow_id` call).

The handler worker uses the same `get_workflow_id` call to generate a workflow ID from a user ID
when it launches the workflow.

The caller workflow:
1. Queries for supported languages (`get_languages` -- backed by a `@workflow.query`)
2. Changes the language to Arabic (`set_language` -- backed by a `@workflow.update` that calls an activity)
3. Confirms the change via a second query (`get_language`)
4. Approves the workflow (`approve` -- backed by a `@workflow.signal`)

### Running

Start a Temporal server:

```bash
temporal server start-dev
```

Create the namespaces and Nexus endpoint:

```bash
temporal operator namespace create --namespace nexus-messaging-handler-namespace
temporal operator namespace create --namespace nexus-messaging-caller-namespace

temporal operator nexus endpoint create \
  --name nexus-messaging-nexus-endpoint \
  --target-namespace nexus-messaging-handler-namespace \
  --target-task-queue nexus-messaging-handler-task-queue
```

In one terminal, start the handler worker:

```bash
uv run python -m nexus_messaging.callerpattern.handler.worker
```

In another terminal, run the caller workflow:

```bash
uv run python -m nexus_messaging.callerpattern.caller.app
```

Expected output:

```
Supported languages: [<Language.CHINESE: 2>, <Language.ENGLISH: 3>]
Language changed: ENGLISH -> ARABIC
Workflow approved
```
