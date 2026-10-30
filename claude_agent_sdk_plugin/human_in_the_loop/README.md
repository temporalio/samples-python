# Human in the Loop

Claude Code pauses before each tool call until a person approves or denies it.

## What this shows

- **A person can sit in the loop for days.** Each approval is a durable wait in the Workflow, so it survives Worker restarts.
- **Approvals are just Workflow state.** A Query shows what's waiting, and an Update decides it. Anything that can call Temporal can be the approval UI.
- **Denial is an answer, not a failure.** A denied command doesn't run, and Claude hears why and carries on.
- **Cancel stops the agent.** Cancelling the Workflow mid-wait ends the turn and stops Claude Code.

## Run it

All commands run from the repository root. Start a Temporal dev server in a separate terminal:

```bash
temporal server start-dev
```

Start the Worker in another terminal. Claude Code works in the Worker's current directory.

```bash
uv run --group claude-agent-sdk claude_agent_sdk_plugin/human_in_the_loop/run_worker.py
```

The Worker runs offline: everything runs for real except the model, which follows a script. To use the real model, put `ANTHROPIC_API_KEY=...` in front of the command.

Start a task:

```bash
temporal workflow start \
  --type HumanInTheLoopWorkflow \
  --task-queue claude-agent-sdk-human-in-the-loop \
  --workflow-id human-in-the-loop \
  --input '"Create hello.txt with a greeting."'
```

See what is waiting for a decision:

```bash
temporal workflow query --workflow-id human-in-the-loop --name pending_tool_calls -o json
```

Approve it, using the `tool_use_id` from the Query. A live model picks its own IDs and may ask for more than one call; decide each one.

```bash
temporal workflow update execute \
  --workflow-id human-in-the-loop \
  --name decide \
  --input '{"tool_use_id": "toolu_hello", "approved": true}'
```

Then get the result:

```bash
temporal workflow result --workflow-id human-in-the-loop
```

Offline, the result is `"Created hello.txt."`, and `hello.txt` is in the Worker's directory, so Claude Code really ran the command.

To deny instead, send `"approved": false`. Offline, the result is `"Understood. I did not create hello.txt."`, and no file appears. The script picks its reply from the tool result in Claude Code's request, so the two replies show your decision reached Claude Code.

To cancel, start another task with a new Workflow ID, then cancel it while a call is pending:

```bash
temporal workflow cancel --workflow-id <workflow-id>
```

The Workflow ends as Canceled. Its history shows the `claude-agent-sdk-close` Activity that stopped Claude Code.
