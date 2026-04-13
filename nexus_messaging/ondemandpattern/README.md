## On-demand pattern

No workflow is pre-started. The caller creates and controls workflow instances through Nexus
operations. `NexusRemoteGreetingService` adds a `run_from_remote` operation that starts a new
`GreetingWorkflow`, and every other operation includes a `workflow_id` so the handler knows which
instance to target.

The caller workflow:
1. Starts two remote `GreetingWorkflow` instances via `run_from_remote` (backed by `workflow_run_operation`)
2. Queries each for supported languages
3. Changes the language on each (Arabic and Hindi)
4. Confirms the changes via queries
5. Approves both workflows
6. Waits for each to complete and returns their results

### Sample directory structure

- [service.py](./service.py) - shared Nexus service definition
- [caller](./caller) - a caller workflow that creates remote workflows and executes Nexus operations, together with a starter
- [handler](./handler) - Nexus operation handlers, together with a workflow started on demand by the Nexus operations, and a worker that polls for workflow, activity, and Nexus tasks

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
uv run python -m nexus_messaging.ondemandpattern.handler.worker
```

In another terminal, run the caller workflow:

```bash
uv run python -m nexus_messaging.ondemandpattern.caller.app
```

Expected output:

```
started remote greeting workflow: UserId One
started remote greeting workflow: UserId Two
Supported languages for UserId One: [<Language.CHINESE: 2>, <Language.ENGLISH: 3>]
Supported languages for UserId Two: [<Language.CHINESE: 2>, <Language.ENGLISH: 3>]
UserId One changed language: ENGLISH -> ARABIC
UserId Two changed language: ENGLISH -> HINDI
Workflows approved
Workflow one result: مرحبا بالعالم
Workflow two result: नमस्ते दुनिया
```
