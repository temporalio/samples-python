This sample demonstrates how to execute Nexus operations directly from client code,
without wrapping them in a workflow. It shows both synchronous and asynchronous
(workflow-backed) operations, plus listing and counting operations.


### Temporal Python SDK support for Standalone Nexus Operations is at [Pre-release](https://docs.temporal.io/evaluate/development-production-features/release-stages#pre-release).

All APIs are experimental and may be subject to backwards-incompatible changes.

Standalone Nexus operations require a server version that supports this feature. Use the dev server build at https://github.com/temporalio/cli/releases/tag/v1.7.2-standalone-nexus-operations.

### Sample directory structure

- [service.py](./service.py) - Nexus service definition with echo (sync) and hello (async) operations
- [handler.py](./handler.py) - Nexus operation handlers and the backing workflow for the async operation
- [worker.py](./worker.py) - Temporal worker that hosts the Nexus service
- [starter.py](./starter.py) - Client that executes standalone Nexus operations


### Instructions

Run the [Temporal dev server build that supports standalone Nexus operations](https://github.com/temporalio/cli/releases/tag/v1.7.2-standalone-nexus-operations). 
(If you are going to run locally, you will want to start it in another terminal; this command is blocking and runs until it receives a SIGINT (Ctrl + C) command.)

Start a Temporal dev server with the dynamic config flags required for standalone Nexus operations:

```bash
temporal server start-dev \
  --dynamic-config-value "nexusoperation.enableStandalone=true" \
  --dynamic-config-value "history.enableChasmCallbacks=true"
```

Create the Nexus endpoint:

```
temporal operator nexus endpoint create \
  --name nexus-standalone-operations-endpoint \
  --target-namespace default \
  --target-task-queue nexus-standalone-operations
```

In one terminal, start the worker:
```
uv run nexus_standalone_operations/worker.py
```

In another terminal, run the starter:
```
uv run nexus_standalone_operations/starter.py
```

### Expected output

```
Echo result: hello
Hello result: Hello, World!

Listing Nexus operations:
  OperationId: echo-..., Operation: echo, Status: COMPLETED
  OperationId: hello-..., Operation: hello, Status: COMPLETED

Total Nexus operations: 2
```

If you run the starter code multiple times, you should see additional operations in the listing results, as more operations are run.
The same goes for the total number of operations.