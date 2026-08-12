# Nexus operation backed by a standalone Activity

This sample shows how to implement a `TemporalOperationHandler` that starts a
standalone Activity as the backing execution for a Nexus operation. When the Activity
finishes, Temporal delivers its result to the Nexus caller. The default handler
cancellation implementation also forwards Nexus cancellation to the Activity.

The APIs used by this sample are experimental and may change incompatibly.

### Sample structure

- [service.py](./service.py) defines the Nexus service shared by caller and handler.
- [activity.py](./activity.py) defines the standalone Activity.
- [handler.py](./handler.py) implements `TemporalOperationHandler.start_operation`.
- [worker.py](./worker.py) hosts the Nexus handler and Activity.
- [starter.py](./starter.py) executes the Nexus operation from client code.

## Run locally

This sample requires the [Temporal dev server build that supports standalone Nexus operations](https://docs.temporal.io/standalone-nexus-operation#temporal-cli-support) and Activity
callbacks enabled.

1. Start the server with caller and handler namespaces:

   ```bash
   ./temporal server start-dev \
     --dynamic-config-value activity.enableCallbacks=true \
     --namespace nexus-standalone-activity-caller \
     --namespace nexus-standalone-activity-handler
   ```

2. Create an endpoint targeting the handler namespace and task queue:

   ```bash
   ./temporal operator nexus endpoint create \
     --name nexus-standalone-activity-endpoint \
     --target-namespace nexus-standalone-activity-handler \
     --target-task-queue nexus-standalone-activity-handler
   ```

3. Start the handler Worker:

   ```bash
   TEMPORAL_NAMESPACE=nexus-standalone-activity-handler \
     uv run nexus_standalone_activity/worker.py
   ```

4. Execute the operation from the caller namespace:

   ```bash
   TEMPORAL_NAMESPACE=nexus-standalone-activity-caller \
     uv run nexus_standalone_activity/starter.py
   ```

Expected output:

```text
Hello, World!
```
