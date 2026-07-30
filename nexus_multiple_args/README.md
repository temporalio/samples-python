This sample shows how to map a Nexus operation to a handler workflow that takes multiple input arguments. The Nexus operation receives a single input object but unpacks it into multiple arguments when starting the workflow.

### Sample directory structure

- [service.py](./service.py) - shared Nexus service definition
- [caller](./caller) - a caller workflow that executes Nexus operations, together with a worker and starter code
- [handler](./handler) - Nexus operation handlers, together with a workflow used by the Nexus operation, and a worker that polls for both workflow and Nexus tasks.

### Instructions

Start a Temporal server. (See the main samples repo [README](../README.md)).

Run the following:

```
temporal operator namespace create --namespace nexus-multiple-args-handler-namespace
temporal operator namespace create --namespace nexus-multiple-args-caller-namespace

temporal operator nexus endpoint create \
  --name nexus-multiple-args-nexus-endpoint \
  --target-namespace nexus-multiple-args-handler-namespace \
  --target-task-queue nexus-multiple-args-handler-task-queue
```

In one terminal, run the Temporal worker in the handler namespace:
```
uv run nexus_multiple_args/handler/worker.py
```

In another terminal, run the Temporal worker in the caller namespace and start the caller workflow:
```
uv run nexus_multiple_args/caller/app.py
```