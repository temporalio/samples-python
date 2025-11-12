This sample shows how to create a Nexus service that is backed by an entity workflow and
exposes synchronous operations that execute queries, updates, signals, and signal-with-start
operations against that workflow. 

The entity workflow follows the entity pattern:
- Runs indefinitely in a loop, processing operations as they arrive
- Maintains state that persists across operations
- Periodically continues-as-new to prevent history from growing too large
- Waits for all handlers to finish before continuing as new

The entity workflow and the queries/updates/signals are private implementation details of the
nexus service: the caller does not know how the operations are implemented.

### Sample directory structure

- [service.py](./service.py) - shared Nexus service definition
- [caller](./caller) - a caller workflow that executes Nexus operations, together with a worker and starter code
- [handler](./handler) - Nexus operation handlers, entity workflow implementation, and a worker that polls for workflow, activity, and Nexus tasks
  - [workflows.py](./handler/workflows.py) - entity workflow that follows the entity pattern
  - [service_handler.py](./handler/service_handler.py) - Nexus operation handlers
  - [worker.py](./handler/worker.py) - worker that runs the entity workflow and handles Nexus operations


### Instructions

Start a Temporal server. (See the main samples repo [README](../README.md)).

Run the following to create the caller and handler namespaces, and the Nexus endpoint:

```
temporal operator namespace create --namespace nexus-sync-operations-handler-namespace
temporal operator namespace create --namespace nexus-sync-operations-caller-namespace

temporal operator nexus endpoint create \
  --name nexus-sync-operations-nexus-endpoint \
  --target-namespace nexus-sync-operations-handler-namespace \
  --target-task-queue nexus-sync-operations-handler-task-queue \
  --description-file nexus_sync_operations/endpoint_description.md
```

In one terminal, run the Temporal worker in the handler namespace:
```
uv run nexus_sync_operations/handler/worker.py
```

In another terminal, run the Temporal worker in the caller namespace and start the caller
workflow:
```
uv run nexus_sync_operations/caller/app.py
```
