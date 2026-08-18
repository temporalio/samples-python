# Sandbox OpenAI Agents

> **Pre-release.** Sandbox support in `temporalio.contrib.openai_agents` is
> subject to change before general availability.

Before running this example, be sure to review the
[prerequisites and background on the integration](../README.md).

`SandboxAgent` from the OpenAI Agents SDK gives an agent a machine to work on:
a shell it can run commands in and a filesystem it can read and write. The
plugin runs every one of those operations as a Temporal activity against a
`SandboxClientProvider` registered on the worker, so sandbox work is
observable, retryable, and recoverable like any other activity. The sandbox
session state is serialized with the workflow, so a worker restart part-way
through a run resumes against the same session.

The workflow refers to a backend by name. `temporal_sandbox_client("local")`
resolves to whichever `SandboxClientProvider` the worker registered under
`"local"`, and the name becomes the prefix of that backend's activity names —
which is what lets several backends coexist on one worker. Names must match
exactly.

This sample uses `UnixLocalSandboxClient`, which runs commands on the worker
host and needs no credentials beyond `OPENAI_API_KEY`. **The agent gets a real
shell on the machine running the worker**, so treat it accordingly: for
anything you would not run locally, register a remote client such as
`DaytonaSandboxClient` or `E2BSandboxClient` from
`agents.extensions.sandbox` instead. Only the worker changes — the workflow
still just names a provider.

## Running the Example

First, start the worker:

```bash
uv run openai_agents/sandbox/run_worker.py
```

Then, in another terminal, run the workflow:

```bash
uv run openai_agents/sandbox/run_local_sandbox_workflow.py
```

The agent writes a file in the sandbox, reads it back, and reports what it
found. In the Web UI at http://localhost:8233 the run shows the model
activities interleaved with the `local-sandbox_session_*` activities that carry
out the sandbox work.

## Notes

* A default `SandboxAgent` already carries the `Filesystem`, `Shell`, and
  `Compaction` capabilities, so this sample declares no tools of its own.
* `temporal_sandbox_client()` takes an optional `ActivityConfig` for timeouts
  and retries on the sandbox activities. It defaults to a 5-minute
  `start_to_close_timeout`.
* A single workflow can target several backends by calling
  `temporal_sandbox_client()` once per name, as long as the worker registers a
  provider for each.
