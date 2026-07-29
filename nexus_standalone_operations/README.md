This sample demonstrates how to execute Nexus operations directly from client code,
without wrapping them in a workflow. It shows both synchronous and asynchronous
(workflow-backed) operations, plus listing and counting operations.

The starter and worker connect to two different namespaces (a "caller" namespace and a "handler"
namespace) — this mirrors how Nexus is typically used to cross namespace boundaries. The client is
configured via the SDK's [environment configuration](https://docs.temporal.io/develop/environment-configuration)
support (`ClientConfig.load_client_connect_config()`), which reads `TEMPORAL_NAMESPACE`,
`TEMPORAL_ADDRESS`, etc. from the environment (and optionally profiles from `temporal.toml`).

### Temporal Python SDK support for Standalone Nexus Operations is at [Pre-release](https://docs.temporal.io/evaluate/development-production-features/release-stages#pre-release).

All APIs are experimental and may be subject to backwards-incompatible changes.

Standalone Nexus operations require a server version that supports this feature. Use the dev server build at https://github.com/temporalio/cli/releases/tag/v1.7.4-standalone-nexus-operations.

### Sample directory structure

- [service.py](./service.py) - Nexus service definition with echo (sync) and hello (async) operations
- [handler.py](./handler.py) - Nexus operation handlers and the backing workflow for the async operation
- [worker.py](./worker.py) - Temporal worker that hosts the Nexus service
- [starter.py](./starter.py) - Client that executes standalone Nexus operations

## Run locally against a dev server

1. Start the [Temporal dev server build that supports standalone Nexus operations](https://docs.temporal.io/standalone-nexus-operation#temporal-cli-support) with the required namespaces pre-created:

   ```bash
   ./temporal server start-dev \
     --namespace my-caller-namespace \
     --namespace my-handler-namespace
   ```

2. Create a Nexus endpoint that routes to the handler namespace and the worker's task queue:

   ```bash
   ./temporal operator nexus endpoint create \
     --name my-nexus-endpoint \
     --target-namespace my-handler-namespace \
     --target-task-queue nexus-handler-queue
   ```

3. In a second terminal, start the worker in the handler namespace:

   ```bash
   TEMPORAL_NAMESPACE=my-handler-namespace uv run nexus_standalone_operations/worker.py
   ```

4. In a third terminal, run the starter in the caller namespace:

   ```bash
   TEMPORAL_NAMESPACE=my-caller-namespace uv run nexus_standalone_operations/starter.py
   ```

### Expected output

```
Echo result: hello
Echo result from existing operation handle: hello

Started `MyNexusService.Hello`. OperationID: hello-...
`MyNexusService.Hello` result: Hello, World!

Listing Nexus operations:
  OperationId: echo-..., Operation: echo, Status: COMPLETED
  OperationId: hello-..., Operation: hello, Status: COMPLETED

Total Nexus operations: 2
```

If you run the starter code multiple times, you should see additional operations in the listing results, as more operations are run.
The same goes for the total number of operations.

## Run against Temporal Cloud

1. Create two namespaces in Temporal Cloud (for example `my-caller-namespace.<account>` and
   `my-handler-namespace.<account>`) and generate an API key (or mTLS cert) that can access both.

2. Create a Nexus endpoint that targets the handler namespace and the worker's task queue. See the
   Temporal Cloud instructions at https://docs.temporal.io/nexus/registry#create-a-nexus-endpoint.
   Use:
   - Endpoint name: `my-nexus-endpoint`
   - Target namespace: `my-handler-namespace.<account>`
   - Target task queue: `nexus-handler-queue`
   - Allowed caller namespaces: include `my-caller-namespace.<account>` (endpoints reject callers
     that are not on this list)

3. Add two profiles to your [environment configuration file](https://docs.temporal.io/develop/environment-configuration),
   one per namespace. Using API keys:

   ```toml
   [profile.handler]
   address = "<region>.<cloud>.api.temporal.io:7233"
   namespace = "my-handler-namespace.<account>"
   api_key = "<your-api-key>"

   [profile.caller]
   address = "<region>.<cloud>.api.temporal.io:7233"
   namespace = "my-caller-namespace.<account>"
   api_key = "<your-api-key>"
   ```

   For mTLS instead of API keys, set `tls.client_cert_path` and `tls.client_key_path` on each profile
   (see the [docs](https://docs.temporal.io/develop/environment-configuration) for the full schema).

4. Run the worker and starter in separate terminals, selecting the appropriate profile in each:

   ```bash
   # terminal 1 (worker, handler namespace)
   TEMPORAL_PROFILE=handler uv run nexus_standalone_operations/worker.py
   ```

   ```bash
   # terminal 2 (starter, caller namespace)
   TEMPORAL_PROFILE=caller uv run nexus_standalone_operations/starter.py
   ```
