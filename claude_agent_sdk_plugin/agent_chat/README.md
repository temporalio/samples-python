# Agent Chat

A multi-turn chat with Claude that lives in one Workflow. Each message is a `send_message` Update that returns Claude's reply, and the `end_conversation` Signal ends the chat. Start here.

## What this shows

- **A chat is just a Workflow.** You write ordinary `ClaudeSDKClient` code, and each message becomes a durable Update with Claude's reply as the result.
- **Chats can run forever.** The Workflow continues as new every few turns, so its history stays small no matter how long the conversation gets.
- **Claude doesn't forget.** Only the session ID crosses to the next run. Claude Code reloads the full conversation from its own session file, so nothing is lost and nothing large is stored in Temporal.

## Run it

All commands run from the repository root. Start a Temporal dev server in a separate terminal:

```bash
temporal server start-dev
```

Start the Worker in another terminal.

```bash
uv run --group claude-agent-sdk claude_agent_sdk_plugin/agent_chat/run_worker.py
```

The Worker runs offline: everything runs for real except the model, which replies with how many replies came before. To use the real model, put `ANTHROPIC_API_KEY=...` in front of the command.

### Chat

Start the chat:

```bash
temporal workflow start \
  --type ChatWorkflow \
  --task-queue claude-agent-sdk-agent-chat \
  --workflow-id claude-agent-sdk-agent-chat \
  --input '{}'
```

Send messages, one at a time:

```bash
temporal workflow update execute \
  --workflow-id claude-agent-sdk-agent-chat \
  --name send_message \
  --input '"Hi, my name is Ada."'
```

Each command prints Claude's reply. Send four messages to cross into a new run, then check that Claude remembers.

Each run takes three messages. After the third reply the run is full and hands off to the next one. A message sent in that moment is rejected with `The chat is continuing as new. Send it again.`, so if your fourth message fails, send it again.

Once the fourth reply arrives, check:

- **Live:** ask "What is my name?" and Claude still knows it.
- **Offline:** the fourth reply is `"Offline reply 4 in this conversation."`. The scripted model only counts the earlier replies in the request Claude Code sends, so the 4 shows Claude Code reloaded them in the new run.

See the runs, one `ContinuedAsNew` and one `Running`:

```bash
temporal workflow list --query 'WorkflowId="claude-agent-sdk-agent-chat"'
```

End the chat:

```bash
temporal workflow signal \
  --workflow-id claude-agent-sdk-agent-chat \
  --name end_conversation
```
