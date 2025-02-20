Usually you will want to create a service definition to formalize the service contract.
However it is possible to define a Nexus service and operation handlers without creating a
service definition. This sample demonstrates how to do that. This may be appropriate if
you want to call a Nexus operation that is being executed by a Worker in the same
namespace as the caller: in other words, if the Nexus operation is playing a role similar
to an Activity.

### Instructions

Start a Temporal server.

Run the following:

```
temporal operator namespace create --namespace my-namespace
temporal operator nexus endpoint create \
  --name my-nexus-endpoint \
  --target-namespace my-namespace \
  --target-task-queue my-task-queue
```

From the root of the repo, run
```
uv run hello_nexus/without_service_definition/app.py
```
