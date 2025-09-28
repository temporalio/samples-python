This sample shows how to create a Nexus service that is backed by a long-running workflow and
exposes operations that use signals, queries, and updates against that workflow.

### Sample directory structure

- [service.py](./service.py) - shared Nexus service definition
- [caller](./caller) - a caller workflow that executes Nexus operations, together with a worker and starter code
- [handler](./handler) - Nexus operation handlers, together with a workflow used by one of the Nexus operations, and a worker that polls for both workflow, activity, and Nexus tasks.


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
