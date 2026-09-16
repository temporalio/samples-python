# Ticket Triage

An LLM support-ticket triage workflow demonstrating the recommended
Temporal → Arize tracing setup (see [../README.md](../README.md) for the full
runbook).

Flow: `classify_ticket` (LLM) and `lookup_account` (plain activity) run under
a custom `triage` span, the workflow then waits for a human decision delivered
as a workflow **update** (`approve`, with a validator), and on approval
`draft_reply` (LLM) produces the customer reply.

| File | Purpose |
|---|---|
| `workflows.py` | `TicketTriageWorkflow` — deterministic, sandboxed; uses plain OpenTelemetry APIs for the `triage` span; `approve` update handler + validator |
| `activities.py` | The two LLM activities and the plain lookup activity; all I/O lives here. Demo hooks for the retry experiments |
| `worker.py` | Worker with `OpenTelemetryPlugin(add_temporal_spans=True)`; `--replay-stress`, `--fail-first-attempt`, `--slow-classify N` |
| `starter.py` | Opens the root span with the OpenInference trace-level attributes (session = workflow ID, user, input, output, metadata, tags), starts the workflow, sends the approval update, prints the Phoenix trace link; `--decline`, `--pause-before-approval N`, `--workflow-id`, `--user` |

## Run

With Phoenix up, dependencies synced, and the environment loaded (see
[../README.md](../README.md)):

```bash
uv run python -m arize_tracing.ticket_triage.worker
uv run python -m arize_tracing.ticket_triage.starter
uv run python -m arize_tracing.verify_trace --trace-id <printed trace id>
```

Variants:

```bash
uv run python -m arize_tracing.ticket_triage.starter --decline
uv run python -m arize_tracing.verify_trace --trace-id <id> --expect declined

# Replay stress: every workflow task replays the workflow from history —
# the Arize trace must come out identical.
uv run python -m arize_tracing.ticket_triage.worker --replay-stress

# Durability demo: park the workflow awaiting approval for 20s, kill and
# restart the worker meanwhile — one clean trace regardless.
uv run python -m arize_tracing.ticket_triage.starter --pause-before-approval 20

# Retry demo: the first classify_ticket attempt fails; two RunActivity spans.
uv run python -m arize_tracing.ticket_triage.worker --fail-first-attempt
uv run python -m arize_tracing.verify_trace --trace-id <id> --expect-attempts classify_ticket=2
```

## Expected trace

```
ticket-triage                                   CHAIN  (root; session = workflow id, user, input, output, tags)
├─ StartWorkflow:TicketTriageWorkflow           CHAIN
│  └─ RunWorkflow:TicketTriageWorkflow          CHAIN
│     ├─ triage                                 CHAIN
│     │  ├─ StartActivity:classify_ticket → RunActivity:classify_ticket
│     │  │  └─ ChatCompletion                   LLM
│     │  └─ StartActivity:lookup_account  → RunActivity:lookup_account
│     └─ StartActivity:draft_reply → RunActivity:draft_reply
│        └─ ChatCompletion                      LLM
└─ StartWorkflowUpdate:approve                  CHAIN
   ├─ ValidateUpdate:approve                    CHAIN
   └─ HandleUpdate:approve                      CHAIN
```

With `--decline`, the `draft_reply` subtree is absent.
