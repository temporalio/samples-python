# Temporal MCP Sequential Thinking Example

This example demonstrates how to implement a durable MCP (Model Context Protocol) server using Temporal workflows that maintains state for complex, branching thought processes.

- The agent is a Temporal workflow (a durable agent)
- The sequential thinking MCP server is stateful, and hence is also implemented as a Temporal workflow (a durable MCP server)  
- The durable agent communicates with the durable MCP server via nexus

This sample includes two agent workflows:
1. **Basic Agent** (`app.py`) - Demonstrates direct MCP tool calls
2. **LLM-Powered Agent** (`app_with_llm.py`) - Uses an LLM to dynamically generate thoughts for problem-solving

## Setup

```bash
uv sync --group=mcp
```

First, create the Nexus endpoint:
```bash
temporal operator nexus endpoint create \
  --target-namespace default \
  --name mcp-sequential-thinking-nexus-endpoint \
  --target-task-queue mcp-sequential-thinking-task-queue
```

Then start the worker:
```bash
uv run mcp_sequential_thinking/worker.py
```

## Usage

### Basic Agent

Run the basic agent that demonstrates direct MCP tool calls:
```bash
uv run mcp_sequential_thinking/app.py
```

### LLM-Powered Agent

The LLM-powered agent requires an API key for Claude (Anthropic) or OpenAI. Set your API key:
```bash
export ANTHROPIC_API_KEY=your_api_key_here
# or
export OPENAI_API_KEY=your_api_key_here
```

The default model is `claude-3-5-sonnet-20241022`. Other supported Anthropic models include:
- `claude-3-opus-20240229` (most capable, slower)
- `claude-3-5-sonnet-20241022` (recommended, good balance)
- `claude-3-haiku-20240307` (fastest, least capable)

Run the agent with a problem to solve:
```bash
# Use default problem
uv run mcp_sequential_thinking/app_with_llm.py

# Or provide your own problem
uv run mcp_sequential_thinking/app_with_llm.py "How do I design a scalable microservices architecture?"
```

The LLM will use the sequential thinking tool to break down the problem into steps, potentially revising its thinking as it goes, until it reaches a final answer.

## How It Works

The sequential thinking MCP server maintains state across tool invocations:
- **Thought History**: All thoughts are stored in order
- **Branches**: Supports branching for exploring alternative approaches
- **Revisions**: Can revise previous thoughts while maintaining history

The LLM-powered agent:
1. Receives a problem to solve
2. Uses an LLM to generate structured thoughts
3. Calls the sequential thinking tool for each thought
4. Continues until the LLM determines it has reached a satisfactory solution
5. Returns the complete thinking process and final answer
