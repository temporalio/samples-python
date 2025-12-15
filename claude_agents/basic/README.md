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
uv run python -m claude_agents.basic.run_worker
```

**Run the workflow:**
```bash
uv run python -m claude_agents.basic.run_tools_workflow
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

Claude sessions are managed using context managers. The context manager handles the complete activity lifecycle:

```python
async with claude_workflow.claude_session("session-name", config):
    client = SimplifiedClaudeClient(self)
    # Use client to interact with Claude
    await client.close()  # Optional - kept for backwards compatibility
# Context cancels the activity and waits for cleanup before exiting
```

**Important**: The context manager handles all cleanup automatically. When exiting, it cancels the activity and waits for it to complete. The `await client.close()` call is optional and kept for backwards compatibility.

#### Resource Optimization with Pause/Resume

For long-running workflows with idle periods, use `ManagedClaudeSession` to pause/resume the activity:

```python
from temporalio.contrib.claude_agent import ManagedClaudeSession

async with ManagedClaudeSession("session-name", config, self) as session:
    # Activity is running
    result1 = await session.send_query("Create a file")

    # Pause to free resources during idle period
    await session.pause()

    # Sleep without consuming worker resources
    await asyncio.sleep(3600)

    # Resume - Claude remembers previous conversation and files
    result2 = await session.send_query("What's in the file?")
```

Claude's session state (conversation history, filesystem changes) persists across pause/resume because it's stored on the filesystem.

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
        # Extract text from nested message structure
        msg_content = message.get("message", {}).get("content", [])
        for block in msg_content:
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

### Activity Lifecycle Management

The integration includes robust activity lifecycle management:

- **Graceful Shutdown**: When workflows complete, the context manager waits for the Claude activity to shut down cleanly before returning
- **Race Condition Handling**: If Claude sends messages after a workflow completes, they're handled gracefully without errors
- **Coordinated Cleanup**: All background tasks (message readers, heartbeats) coordinate shutdown using internal events
- **Clean Logs**: No spurious "workflow execution already completed" errors in production logs

This ensures that workflows complete cleanly without leaving orphaned activities or noisy error logs.

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

## Next Steps

- See the parent README for more advanced examples
- Check the [Claude Agent SDK documentation](https://github.com/anthropics/claude-agent-sdk-python)
- Explore the [Temporal Python SDK documentation](https://docs.temporal.io/docs/python)