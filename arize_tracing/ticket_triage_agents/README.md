# Ticket Triage with the OpenAI Agents SDK

The same ticket-triage flow as [../ticket_triage/](../ticket_triage/), built
with the [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/)
and traced to Arize through Temporal's `OpenAIAgentsPlugin` (see
[../README.md](../README.md) for the full runbook).

A triage agent looks up the customer's account through a Temporal activity
exposed as a tool (`activity_as_tool`) and classifies the ticket; the workflow
then waits for a human approval (a workflow update), and a reply agent drafts
the reply. Model calls run as Temporal activities.

| File | Purpose |
|---|---|
| `plugin.py` | `OpenAIAgentsPlugin(use_otel_instrumentation=True, add_temporal_spans=True, ...)`: bridges Agents SDK tracing to OpenTelemetry through the OpenInference `openai-agents` instrumentation |
| `workflows.py` | `TicketTriageAgentsWorkflow` — two agents, one activity tool, `approve` update handler + validator |
| `worker.py` | Worker registering the workflow and the `lookup_account` activity; `--role workflows|activities|all`, `--replay-stress` |
| `starter.py` | Opens the Agents SDK trace (which becomes the root AGENT span), sets the OpenInference attributes on it, starts the workflow, sends the approval; `--decline`, `--pause-before-approval N`, `--workflow-id`, `--user` |

Differences from the framework-agnostic scenario:

- The Agents SDK trace is the root span (kind AGENT); Temporal operations
  appear as `temporal:*` CHAIN spans created by the plugin, not as the
  `OpenTelemetryPlugin`'s `StartWorkflow:*`/`RunWorkflow:*` spans. Do not add
  `OpenTelemetryPlugin` as well: the two would produce overlapping spans.
- `setup_tracing()` must run before the plugin is constructed: the plugin
  checks that the global tracer provider is Temporal's replay-safe provider.
- The plugin propagates trace and span IDs but not OpenTelemetry baggage, so
  `session.id` and `user.id` live on the root span (enough for Phoenix's
  Sessions view).
- Run the starter, a workflow worker (`--role workflows`), and an activity
  worker (`--role activities`) as separate processes, as shown. A single
  worker process that runs both exports the `temporal:startActivity` spans
  with a parent that is not in the trace, so the model-call and tool subtrees
  appear detached in Arize until
  [temporalio/sdk-python#1852](https://github.com/temporalio/sdk-python/issues/1852)
  is fixed. The bridge is Public Preview in the Temporal SDK.

## Run

```bash
uv run python -m arize_tracing.ticket_triage_agents.worker --role workflows
uv run python -m arize_tracing.ticket_triage_agents.worker --role activities
uv run python -m arize_tracing.ticket_triage_agents.starter
uv run python -m arize_tracing.verify_trace --trace-id <printed trace id> --scenario agents

# Replay stress and the durability demo work the same way as in ticket_triage:
uv run python -m arize_tracing.ticket_triage_agents.worker --role workflows --replay-stress
uv run python -m arize_tracing.ticket_triage_agents.starter --pause-before-approval 20
```

## Expected trace

```
Ticket triage agents                             AGENT  (root; session, user, input, output)
├─ temporal:startWorkflow:TicketTriageAgentsWorkflow   CHAIN
│  └─ temporal:executeWorkflow                   CHAIN
│     ├─ Agent workflow → Triage agent           AGENT
│     │  ├─ turn                                 CHAIN
│     │  │  └─ temporal:startActivity            CHAIN  (model call)
│     │  │     ├─ temporal:executeActivity → response   LLM
│     │  │     └─ lookup_account                 TOOL
│     │  │        └─ temporal:startActivity → temporal:executeActivity
│     │  └─ turn → temporal:startActivity → temporal:executeActivity → response   LLM
│     └─ Agent workflow → Reply agent            AGENT
│        └─ turn → temporal:startActivity → temporal:executeActivity → response   LLM
└─ temporal:updateWorkflow                       CHAIN
```
