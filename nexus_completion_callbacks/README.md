# Nexus completion callbacks for standalone Nexus operations

This sample shows how to attach a completion callback when starting a standalone Nexus
operation. When the operation finishes, Temporal calls an on-complete Nexus operation on
a Worker you choose, passing the operation's result or failure and a source context
value you supplied at start time. The starter exits right after starting the operation;
the result arrives later at a separate completion Worker.

The APIs used by this sample are experimental and may change incompatibly.

### Sample structure

- [service.py](./service.py) defines the Nexus service shared by caller and handler.
- [handler](./handler) runs in the handler namespace:
  - [service_handler.py](./handler/service_handler.py) implements the operation, backed
    by a standalone Activity.
  - [worker.py](./handler/worker.py) hosts the Nexus handler and Activity.
- [caller](./caller) runs in the caller namespace:
  - [starter.py](./caller/starter.py) starts the Nexus operation with
    `completion_callbacks` and exits without waiting for the result.
  - [completion_handler.py](./caller/completion_handler.py) implements the on-complete
    operation that receives the callback and starts a workflow to record it.
  - [workflows.py](./caller/workflows.py) defines the workflow that logs and records
    each callback's outcome.
  - [completion_worker.py](./caller/completion_worker.py) hosts the on-complete
    operation and the workflow.

## Run locally

Nexus completion callbacks currently require a pre-release Temporal CLI build. Download
[Temporal CLI `v1.9.2-nexus-handler-callbacks`](https://github.com/temporalio/cli/releases/tag/v1.9.2-nexus-handler-callbacks),
extract it, and put the `temporal` executable in the repository root. Run the commands
below from the repository root. They run the pre-release build as `./temporal`, so it
doesn't conflict with any `temporal` CLI you already have installed.

The server and both Workers keep running, so run each step in its own terminal.

1. Start the server with caller and handler namespaces:

   ```bash
   ./temporal server start-dev \
     --dynamic-config-value activity.enableCallbacks=true \
     --namespace nexus-completion-callbacks-caller \
     --namespace nexus-completion-callbacks-handler
   ```

2. Create an endpoint targeting the handler namespace and task queue:

   ```bash
   ./temporal operator nexus endpoint create \
     --name nexus-completion-callbacks-endpoint \
     --target-namespace nexus-completion-callbacks-handler \
     --target-task-queue nexus-handler-task-queue
   ```

3. Start the handler Worker:

   ```bash
   TEMPORAL_NAMESPACE=nexus-completion-callbacks-handler \
     uv run nexus_completion_callbacks/handler/worker.py
   ```

4. Start the completion Worker in the caller namespace:

   ```bash
   TEMPORAL_NAMESPACE=nexus-completion-callbacks-caller \
     uv run nexus_completion_callbacks/caller/completion_worker.py
   ```

5. Start the operation from the caller namespace:

   ```bash
   TEMPORAL_NAMESPACE=nexus-completion-callbacks-caller \
     uv run nexus_completion_callbacks/caller/starter.py
   ```

The starter prints the operation ID and exits:

```text
Started operation greeting-<uuid>
```

When the operation finishes, Temporal delivers the result to the completion Worker by
calling its on-complete operation. The on-complete operation starts a
`RecordCompletionWorkflow`, which logs the result. Switch to the completion Worker's
terminal from step 4 to see it:

```text
INFO:temporalio.workflow:Operation greeting-<uuid> succeeded: Hello, World! ({'attempt': 1, 'namespace': 'nexus-completion-callbacks-caller', 'run_id': '<run-id>', 'task_queue': 'nexus-completion-handler-task-queue', 'workflow_id': 'on-complete-greeting-<uuid>', 'workflow_type': 'RecordCompletionWorkflow'})
```
