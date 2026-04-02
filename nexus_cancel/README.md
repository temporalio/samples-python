# Nexus Cancellation

This sample shows how a caller workflow can fan out multiple Nexus operations concurrently, take the first result, and cancel the rest using `WAIT_REQUESTED` cancellation semantics.

With `WAIT_REQUESTED`, the caller proceeds once the handler has received the cancel request — it does not wait for the handler to finish processing the cancellation.

Start a Temporal server. (See the main samples repo [README](../README.md)).

Run the following:

```
temporal operator namespace create --namespace nexus-cancel-handler-namespace
temporal operator namespace create --namespace nexus-cancel-caller-namespace

temporal operator nexus endpoint create \
  --name nexus-cancel-endpoint \
  --target-namespace nexus-cancel-handler-namespace \
  --target-task-queue nexus-cancel-handler-task-queue
```

Next, in separate terminal windows:

## Nexus Handler Worker

```bash
uv run nexus_cancel/handler/worker.py
```

## Nexus Caller App

```bash
uv run nexus_cancel/caller/app.py
```

## Expected Output

On the caller side, you should see a greeting in whichever language completed first:
```
Hello Nexus 👋
```

On the handler side, you should see cancellation log messages for the remaining operations:
```
HelloHandlerWorkflow was cancelled successfully.
HelloHandlerWorkflow was cancelled successfully.
HelloHandlerWorkflow was cancelled successfully.
HelloHandlerWorkflow was cancelled successfully.
```

The caller workflow returns before all handler workflows have completed their cancellation cleanup. This demonstrates `WAIT_REQUESTED` semantics: the caller didn't wait for the handler workflows to finish, but still guaranteed that all handlers received the cancellation request.
