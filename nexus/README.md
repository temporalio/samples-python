# nexus

Temporal Nexus is a new feature of the Temporal platform designed to connect durable executions across team, namespace,
region, and cloud boundaries. It promotes a more modular architecture for sharing a subset of your team’s capabilities
via well-defined service API contracts for other teams to use, that abstract underlying Temporal primitives, like
Workflows, or execute arbitrary code.

Learn more at [temporal.io/nexus](https://temporal.io/nexus).

This sample shows how to use Temporal for authoring a Nexus service and call it from a workflow.

### Sample directory structure

- [service](./service) - shared service defintion
- [caller](./caller) - caller workflows, worker, and starter
- [handler](./handler) - handler workflow, operations, and worker
- [options](./options) - command line argument parsing utility

## Getting started locally

### Get `temporal` CLI to enable local development

1. Follow the instructions on the [docs
   site](https://learn.temporal.io/getting_started/go/dev_environment/#set-up-a-local-temporal-service-for-development-with-temporal-cli)
   to install Temporal CLI.

> NOTE: Required version is at least v1.1.0.

### Spin up environment

#### Start temporal server

> HTTP port is required for Nexus communications

```
temporal server start-dev --http-port 7243 --dynamic-config-value system.enableNexus=true
```

### Initialize environment

#### Create caller and target namespaces

```
temporal operator namespace create --namespace my-target-namespace
temporal operator namespace create --namespace my-caller-namespace
```

#### Create Nexus endpoint

```
temporal operator nexus endpoint create \
  --name my-nexus-endpoint-name \
  --target-namespace my-target-namespace \
  --target-task-queue my-target-task-queue \
  --description-file ./nexus/service/description.md
```

### Start Nexus handler worker
```
uv run python nexus/handler/worker.py
```

### Run Nexus caller application (worker + starter)
```
uv run python nexus/caller/app.py
```

### Output

TODO
