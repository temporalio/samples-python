## On-demand pattern

No Workflow is pre-started. The caller creates and controls Workflow instances through Nexus
operations. `NexusRemoteGreetingService` adds a `run_from_remote` operation that starts a new
`GreetingWorkflow`, and every other operation includes a `user_id` so the handler knows which
instance to target.

The caller Workflow:
1. Attaches approval context for the first user via `attach_approval_context`, before anything has
   started that user's Workflow
2. Starts two remote `GreetingWorkflow` instances via `run_from_remote` (backed by `temporal_operation`)
3. Attaches approval context for the second user, whose Workflow now already exists
4. Queries each for supported languages
5. Changes the language on each (Arabic and Hindi)
6. Confirms the changes via queries
7. Approves both Workflows
8. Waits for each to complete and returns their results

### Running

This sample requires a Temporal dev server build that supports Workflow Update callbacks. Download the compatible
binary from the [Temporal CLI pre-release instructions](https://docs.temporal.io/standalone-nexus-operation#temporal-cli-support).

Start the Temporal dev server with the required namespaces pre-created and Workflow Update callbacks enabled:

```bash
./temporal server start-dev \
  --dynamic-config-value history.enableUpdateCallbacks=true \
  --dynamic-config-value history.enableCHASMSignalBacklinks=true \
  --dynamic-config-value history.enableSignalWithStartFromWorkflow=true \
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
uv run python -m nexus_messaging.ondemandpattern.handler.worker
```

In another terminal, run the following command to start the example:

```bash
uv run python -m nexus_messaging.ondemandpattern.caller.app
```

Expected output:

```
Attached approval context before the workflow existed: UserId One
started remote greeting workflow: UserId One
started remote greeting workflow: UserId Two
Attached approval context to the running workflow: UserId Two
Supported languages for UserId One: [<Language.CHINESE: 2>, <Language.ENGLISH: 3>]
Supported languages for UserId Two: [<Language.CHINESE: 2>, <Language.ENGLISH: 3>]
UserId One changed language: ENGLISH -> ARABIC
UserId Two changed language: ENGLISH -> HINDI
Workflows approved
Workflow one result: مرحبا بالعالم
Workflow two result: नमस्ते दुनिया
```
