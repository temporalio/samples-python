# Nexus Cancellation

This sample shows how to cancel a Nexus operation from a caller workflow and specify a cancellation type. In this sample we show using the `WAIT_REQUESTED` cancellation type, which allows the caller to return after the handler workflow has received the request to be cancelled, but does not wait for the handler workflow to finish processing the cancellation request.

To run this sample, set up your environment following the instructions in the main [Nexus Sample](../hello_nexus/README.md).

Next, in separate terminal windows:

## Nexus Handler Worker

```bash
uv run nexus_cancel/handler/worker.py
```

## Nexus Caller Worker

```bash
uv run nexus_cancel/caller/worker.py
```

## Start Caller Workflow

```bash
uv run nexus_cancel/caller/starter.py
```

## Expected Output

On the caller side, you should see:
```
Started workflow workflowId: hello-caller-<uuid> runId: <run-id>
Workflow result: Hello Nexus-X 👋
```

On the handler side, you should see multiple log messages:
```
HelloHandlerWorkflow was cancelled successfully.
HelloHandlerWorkflow was cancelled successfully.
HelloHandlerWorkflow was cancelled successfully.
HelloHandlerWorkflow was cancelled successfully.
```

Notice the timing: the caller workflow returns before all handler workflows have completed their cancellation cleanup. This is because of the use of `WAIT_REQUESTED` as the cancellation type in the Nexus operation. This means the caller didn't have to wait for the handler workflows to finish, but still guarantees the handler workflows will receive the cancellation request.
