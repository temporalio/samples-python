This sample shows how to define a Nexus service, implement the operation handlers, and
call the operations from a workflow.

### Sample directory structure

- [service.py](./service.py) - shared Nexus service definition
- [caller](./caller) - a caller workflow that executes Nexus operations, together with a worker and starter code
- [handler](./handler) - Nexus operation handlers, together with a workflow used by one of the Nexus operations, and a worker that polls for both workflow and Nexus tasks.


### Instructions

Start a Temporal server. (See the main samples repo [README](../README.md)).

Run the following:

```
temporal operator namespace create --namespace hello-nexus-basic-handler-namespace
temporal operator namespace create --namespace hello-nexus-basic-caller-namespace

temporal operator nexus endpoint create \
  --name hello-nexus-basic-nexus-endpoint \
  --target-namespace hello-nexus-basic-handler-namespace \
  --target-task-queue my-handler-task-queue \
  --description-file hello_nexus/endpoint_description.md
```

In one terminal, run the Temporal worker in the handler namespace:
```
uv run hello_nexus/handler/worker.py
```

In another terminal, run the Temporal worker in the caller namespace and start the caller
workflow:
```
uv run hello_nexus/caller/app.py
```
