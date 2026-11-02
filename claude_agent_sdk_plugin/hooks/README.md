# Hooks

A `PreToolUse` hook that runs in the Workflow. It blocks Bash commands that delete files and records each one through an Activity.

## What this shows

- **Hooks are plain functions.** You pass them in `ClaudeAgentOptions.hooks` as usual, and they run in the Workflow.
- **A hook can run Activities.** `check_command` calls the `audit_command` Activity, with Temporal's retries and timeouts.
- **A hook decides for Claude Code.** Returning `permissionDecision: "deny"` stops the tool call, and Claude hears why and carries on.

## Run it

All commands run from the repository root. Start a Temporal dev server in a separate terminal:

```bash
temporal server start-dev
```

Start the Worker in another terminal.

```bash
uv run --group claude-agent-sdk claude_agent_sdk_plugin/hooks/run_worker.py
```

The Worker runs offline: everything runs for real except the model, which is scripted to run `echo hello` and then `rm hello.txt`. To use the real model, put `ANTHROPIC_API_KEY=...` in front of the command. The live model words its reply differently each time.

### Start the Workflow

```bash
temporal workflow execute \
  --type HooksWorkflow \
  --task-queue claude-agent-sdk-hooks \
  --workflow-id claude-agent-sdk-hooks \
  --input '"Run echo hello, then delete hello.txt."'
```

Offline, the final reply is scripted (live, Claude describes the same block in its own words):

```text
"The command that deletes hello.txt was blocked."
```

## See the boundary

In the Temporal UI (`http://localhost:8233`), the `audit_command` Activity ran once, for the blocked `rm` command. The hook lets `echo hello` through without an Activity.
