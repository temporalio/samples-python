# Claude Agent SDK Basic Examples

This directory contains basic examples demonstrating the Claude Agent SDK integration with Temporal workflows.

## Prerequisites

1. Install dependencies:
```bash
# From the samples-python directory
uv sync --group claude-agents
```

2. Start a Temporal server:
```bash
temporal server start-dev
```

3. Set your Claude API key:
```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

## Examples

### Hello World Workflow

The simplest example - Claude responds to prompts in haiku format.

**Run the worker:**
```bash
uv run python -m claude_agents.basic.run_worker
```

**In another terminal, run the workflow:**
```bash
uv run python -m claude_agents.basic.run_hello_world_workflow
```

### Tools Workflow

Demonstrates using Temporal activities as tools that Claude can invoke.

**Run the worker (if not already running):**
```bash
python -m claude_agents.basic.run_worker
```

**Run the workflow:**
```bash
python -m claude_agents.basic.run_tools_workflow
```

This example shows Claude using a weather tool to answer questions about weather conditions.

## Key Concepts

### ClaudeMessageReceiver Mixin

All Claude workflows must inherit from `ClaudeMessageReceiver` and call `init_claude_receiver()`:

```python
@workflow.defn
class MyWorkflow(ClaudeMessageReceiver):
    @workflow.run
    async def run(self):
        self.init_claude_receiver()
        # ... rest of workflow
```

### Session Management

Claude sessions are managed using context managers:

```python
async with claude_workflow.claude_session("session-name", config):
    client = SimplifiedClaudeClient(self)
    # Use client to interact with Claude
```

### Configuration

Use `ClaudeSessionConfig` to configure Claude's behavior:

```python
config = ClaudeSessionConfig(
    system_prompt="Your instructions here",
    max_turns=3,
    allowed_tools=["tool1", "tool2"],
)
```

### Message Processing

Process Claude's responses by iterating over messages:

```python
async for message in client.send_query(prompt):
    if message.get("type") == "assistant":
        for block in message.get("content", []):
            if block.get("type") == "text":
                result += block.get("text", "")
```

## Architecture

The Claude Agent SDK integration uses a three-layer architecture:

1. **Workflow Layer**: Your business logic using the `ClaudeMessageReceiver` mixin
2. **Activity Layer**: Manages Claude subprocess and message routing
3. **Claude SDK Layer**: The actual Claude Agent SDK running in a subprocess

This design ensures:
- Workflow determinism (all I/O happens in activities)
- State persistence (conversations survive worker restarts)
- Proper isolation (Claude SDK runs outside the workflow sandbox)

## Differences from OpenAI Agents

| Feature | OpenAI Agents | Claude Agents |
|---------|--------------|---------------|
| Agent Creation | `Agent()` class | Session-based with config |
| Execution | `Runner.run()` | `SimplifiedClaudeClient.send_query()` |
| Tools | Function decorators | Activity-based with `allowed_tools` |
| Message Handling | Direct return | Async iteration over messages |
| Session Management | Implicit | Explicit with context manager |

## Troubleshooting

### Import Errors
Make sure you've installed the dependencies with the claude-agents group:
```bash
uv sync --group claude-agents
```

### API Key Issues
Ensure your Anthropic API key is set:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Timeout Errors
Increase the activity timeout in your session configuration if Claude needs more time to respond.

### Multi-turn Conversations
The current implementation has a known issue with multi-turn conversations timing out. This is being actively debugged.

## Next Steps

- See the parent README for more advanced examples
- Check the [Claude Agent SDK documentation](https://github.com/anthropics/claude-agent-sdk-python)
- Explore the [Temporal Python SDK documentation](https://docs.temporal.io/docs/python)