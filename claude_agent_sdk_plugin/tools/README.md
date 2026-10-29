# Tools

Claude calls two custom Claude Agent SDK `@tool` functions that run in the Workflow. `count_letter` is plain Workflow code, and `get_weather` calls the `fetch_weather` Activity for its I/O.

## What this shows

- **Tools are plain `@tool` functions.** You write them as usual with the Claude Agent SDK, and they run in the Workflow.

## Run it

All commands run from the repository root. Start a Temporal dev server in a separate terminal:

```bash
temporal server start-dev
```

Start the Worker in another terminal.

```bash
uv run --group claude-agent-sdk claude_agent_sdk_plugin/tools/run_worker.py
```

The Worker runs offline: everything runs for real except the model, which is scripted to call both tools. To use the real model, put `ANTHROPIC_API_KEY=...` in front of the command.

### Start the Workflow

```bash
temporal workflow execute \
  --type ToolsWorkflow \
  --task-queue claude-agent-sdk-tools \
  --workflow-id claude-agent-sdk-tools \
  --input '"Count the r letters in strawberry, then get the weather in Paris."'
```

Offline, the final reply is scripted:

```text
"There are 3 r's in strawberry. It is 21 C and sunny in Paris."
```

## See the boundary

The history is the real proof, live or offline. In the Temporal UI (`http://localhost:8233`) or with `temporal workflow show --workflow-id claude-agent-sdk-tools`, the weather call is one `fetch_weather` Activity. `count_letter` has none; it ran as Workflow code. The other Activities are the plugin's `claude-agent-sdk-*` Activities, which reach Claude Code.
