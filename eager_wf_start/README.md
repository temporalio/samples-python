# Eager Workflow Start

This sample shows how to create a workflow that uses Eager Workflow Start.

Eager Workflow Start is feature that reduces the time it takes to start a Workflow. The target use case is short-lived Workflows that interact with other services using Local Activities, as such, we'll be using Local Activities in this sample.

You can read more about Eager Workflow Start in our:

- [Eager Workflow Start blog](https://temporal.io/blog/improving-latency-with-eager-workflow-start)
- [Worker Performance Docs](https://docs.temporal.io/develop/worker-performance#eager-workflow-start)

To run, first see the main [README.md](../README.md) for prerequisites.

Then run the sample via:

    uv run eager_wf_start/run.py