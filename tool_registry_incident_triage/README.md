# Python: incident-triage tool-registry sample

Demonstrates `temporalio.contrib.tool_registry` end-to-end: long-running `AgenticSession` activity, MCP HTTP integration, human-in-the-loop via companion workflow, and a testable activity refactor.

## What's here

| File | Purpose |
|---|---|
| `triage_types.py` | `AlertPayload`, `TriageResult`, `ApprovalRequest`, `ApprovalResponse` records. |
| `triage_activity.py` | The activity. Defines `TriageDeps` (record of I/O callables), `build_triage_registry(alert, session, deps)` returning `(registry, get_result)`, and the activity entrypoint that wires production deps. |
| `triage_workflow.py` | Workflow that schedules the activity with `agentic` timeout profile. |
| `approval_workflow.py` | Companion HITL workflow: deterministic ID per alert, two signals (request/decision), one query (pending). |
| `worker.py` | Worker registration. |
| `client.py` | Demo client to start a workflow. |
| `tests/test_triage_activity.py` | Unit tests demonstrating `MockProvider` + `TriageDeps` pattern. Run: `pytest tests/`. |

## Run

```bash
# 1. Run a Temporal dev server (separate terminal)
temporal server start-dev

# 2. Set up env
export ANTHROPIC_API_KEY=sk-ant-...
export PROM_MCP=http://localhost:7070/mcp
export K8S_MCP=http://localhost:7071/mcp

# 3. Start the worker
python worker.py

# 4. Start a workflow
python client.py
```

Tests don't need a Temporal server or API key.

## Requires

- `temporalio` with `tool_registry` contrib (currently the `feat/tool-registry` branch — install from source or wait for the next release).
- `anthropic` Python SDK (peer dep).
- `httpx` for MCP HTTP calls.
