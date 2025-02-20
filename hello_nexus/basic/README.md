This sample shows how to define a Nexus service, implement the operation handlers, and
call the operations from a workflow.

### Sample directory structure

- [service.py](./service.py) - shared Nexus service definition
- [caller](./caller) - a caller workflow that executes Nexus operations, together with a worker and starter code
- [handler](./handler) - Nexus operation handlers, together with a workflow used by one of the Nexus operations, and a worker that polls for both workflow and Nexus tasks.


### Instructions

Start a Temporal server.

Run the following:

```
temporal operator namespace create --namespace my-target-namespace
temporal operator namespace create --namespace my-caller-namespace

temporal operator nexus endpoint create \
  --name my-nexus-endpoint \
  --target-namespace my-target-namespace \
  --target-task-queue my-target-task-queue \
  --description-file ./hello_nexus/basic/service_description.md
```

In one terminal, run the Temporal worker in the handler namespace:
```
uv run hello_nexus/basic/handler/worker.py
```

In another terminal, run the Temporal worker in the caller namespace and start the caller
workflow:
```
uv run hello_nexus/basic/caller/app.py
```
