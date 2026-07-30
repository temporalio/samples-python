# Basic — Single Agent, One Model Call

The minimal Google ADK + Temporal sample: an ordinary ADK `Agent` whose
`model=TemporalModel("gemini-2.5-flash")`, driven by an `InMemoryRunner` inside
a workflow. No tools, no streaming — just one model turn.

It demonstrates that `GoogleAdkPlugin`'s deterministic runtime and Pydantic
payload converter let an unmodified ADK agent run durably in a workflow, with
every LLM call surfaced as an `invoke_model` activity.

Before running, review the [prerequisites in the suite README](../README.md)
(Temporal dev server, `uv sync --group google-adk`, and
`export GOOGLE_API_KEY=...`).

## Running

Start the worker in one terminal:

```bash
uv run python -m google_adk_agents.basic.run_worker
```

Then start the workflow in another terminal:

```bash
uv run python -m google_adk_agents.basic.run_hello_world_workflow
```

## What to expect

The starter prints the agent's response — a haiku about recursion. The agent is
instructed to respond only in haikus.

## In the Temporal UI

Open the workflow `google-adk-agents-basic-workflow-id`. In the history you will
see one `invoke_model` activity for the single model turn. That activity is
where the call to Gemini actually happens — the workflow itself stays
deterministic and replay-safe.
