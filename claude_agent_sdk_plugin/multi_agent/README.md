# Multi-Agent

Claude Code's native subagent delegation, run as a Temporal Workflow. A coordinator delegates to two subagents defined in `ClaudeAgentOptions(agents=...)`: a `researcher` that gathers facts and a `writer` that turns them into a briefing.

## What this shows

- **Claude Code's own subagents, made durable.** You define roles with `AgentDefinition` as usual, and Claude Code delegates to them inside one process. Temporal adds durability without changing how delegation works.
- **You can see who said what.** Every subagent message points back to the call that started it, so the Workflow can return and log each role's output separately.
- **No person needed.** Delegation is pre-approved, so the team runs end to end on its own.

## Run it

All commands run from the repository root. Start a Temporal dev server in a separate terminal:

```bash
temporal server start-dev
```

Start the Worker in another terminal.

```bash
uv run --group claude-agent-sdk claude_agent_sdk_plugin/multi_agent/run_worker.py
```

The Worker runs offline: everything runs for real except the model, which follows a script. To use the real model, put `ANTHROPIC_API_KEY=...` in front of the command.

Then run the Workflow:

```bash
temporal workflow execute \
  --type MultiAgentWorkflow \
  --task-queue claude-agent-sdk-multi-agent \
  --workflow-id multi-agent \
  --input '"durable execution"'
```

## Expected behavior

The result has the final briefing and, under `messages_by_agent`, what each of `coordinator`, `researcher`, and `writer` said. The Workflow also logs each message with its role.

Offline, the researcher returns three facts, the writer one sentence, and the coordinator `Final briefing: Temporal keeps your code running through failures.` The script answers the researcher and writer only when it sees their prompts, so those replies show Claude Code really ran each subagent. The grouping by role comes from Claude Code's real messages.

If the Worker restarts mid-run, the Workflow resumes the session on the restarted Worker. Claude Code finishes the cut-off turn.
