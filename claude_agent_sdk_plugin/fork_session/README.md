# Fork Session

Answer a prompt once, then try several follow-ups at the same time, each in its own fork of that conversation. Every fork starts from the same history, and the original session stays as it was.

## What this shows

- **Branching a conversation.** `fork_session=True` with `resume` starts a new session from a copy of an existing one, as in the Claude Agent SDK.
- **Session IDs from Claude Code.** The Workflow reads each session's ID from Claude Code's `init` message, including each fork's. If the connection is lost, it resumes that session, or starts it again if Claude Code hadn't yet started it.
- **Forks in parallel.** Each fork is its own Claude Code. The Workflow runs them together with `asyncio.gather`.

## Run it

All commands run from the repository root. Start a Temporal dev server in a separate terminal:

```bash
temporal server start-dev
```

Start the Worker in another terminal:

```bash
uv run --group claude-agent-sdk claude_agent_sdk_plugin/fork_session/run_worker.py
```

The Worker runs offline: everything runs for real except the model, which answers with fixed text. To use the real model, put `ANTHROPIC_API_KEY=...` in front of the command.

Run the Workflow from a third terminal, with the prompt and a list of follow-ups:

```bash
temporal workflow execute \
  --type ForkSessionWorkflow \
  --task-queue claude-agent-sdk-fork-session \
  --workflow-id fork-session \
  --input '"Plan a weekend in Lisbon."' \
  --input '["Redo it on a tight budget.", "Redo it with no budget limit."]'
```

## Expected behavior

The result has one branch per follow-up, each with its own session ID. Offline, it is:

```json
[
  {"answer": "Walk Alfama, catch a free fado night, take the tram to Belém.", "prompt": "Redo it on a tight budget.", "session_id": "8889ec93-..."},
  {"answer": "A private fado dinner, then a yacht along the Tagus to Belém.", "prompt": "Redo it with no budget limit.", "session_id": "3a14ddda-..."}
]
```

Each fork's model request has the weekend plan from the base conversation, and neither has the other fork's follow-up. To continue a branch later, start a client with `resume` set to its session ID.
