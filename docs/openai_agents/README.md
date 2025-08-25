# OpenAI Agents SDK Integration with Temporal

⚠️ **Public Preview** - This integration is experimental and its interfaces may change prior to General Availability.

This directory contains comprehensive examples demonstrating how to integrate the [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) with Temporal's durable execution engine. These samples extend the OpenAI Agents SDK examples with Temporal's durability, orchestration, and observability capabilities.

## 🏗️ **Architecture Overview**

The integration creates a powerful synergy between two technologies:

- **Temporal Workflows**: Provide durable execution, state management, and orchestration
- **OpenAI Agents SDK**: Deliver AI agent capabilities, tool integration, and LLM interactions

This combination ensures that AI agent workflows are:
- **Durable**: Survive interruptions, restarts, and failures
- **Observable**: Full tracing, monitoring, and debugging capabilities
- **Scalable**: Handle complex multi-agent interactions and long-running conversations
- **Reliable**: Built-in retry mechanisms and error handling

## 🚀 **Key Integration Benefits**

### **Implicit Activity Creation**
Every agent invocation is automatically executed through a Temporal Activity, providing durability without code changes. The `Runner.run()` calls automatically create activities under the hood.

### **Integrated Tracing**
Unified observability across both Temporal and OpenAI systems. View agent execution in Temporal's workflow history and OpenAI's tracing dashboard simultaneously.

### **Horizontal Scaling**
Each agent runs in its own process or thread, enabling independent scaling. Add more capacity for specific agent types without affecting others.

### **Production Readiness**
- **Crash-Proof Execution**: Automatic recovery from failures, restarts, and bugs
- **Rate Limit Handling**: Graceful handling of LLM API rate limits
- **Network Resilience**: Automatic retries for downstream API failures
- **State Persistence**: Workflow state automatically saved between steps

## 🔄 **Core Integration Patterns**

### **Workflow-Orchestrated Agents**
Temporal workflows orchestrate the entire agent lifecycle, from initialization to completion, ensuring state persistence and fault tolerance.

### **Agent State Management**
Workflows maintain conversation state, agent context, and execution history, enabling long-running, stateful AI interactions.

### **Tool Integration**
Seamless integration of OpenAI's built-in tools (web search, code interpreter, file search) with custom Temporal activities for I/O operations.

### **Multi-Agent Coordination**
Complex workflows can coordinate multiple specialized agents, each with distinct roles and responsibilities.

## 📚 **Documentation Structure**

### **Getting Started**
- **[llms.txt](./llms.txt)** - LLM-friendly summary for AI assistants and developers
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Technical deep dive into integration patterns

### **Core Services**
- **[Basic Examples](./BASIC.md)** - Fundamental agent patterns, lifecycle management, and tool integration
- **[Agent Patterns](./AGENT_PATTERNS.md)** - Advanced multi-agent architectures, routing, and coordination patterns
- **[Tools Integration](./TOOLS.md)** - Comprehensive tool usage including code interpreter, file search, and image generation

### **Specialized Workflows**
- **[Handoffs](./HANDOFFS.md)** - Agent collaboration and message filtering patterns
- **[Hosted MCP](./HOSTED_MCP.md)** - Model Context Protocol integration for external tool access
- **[Model Providers](./MODEL_PROVIDERS.md)** - Custom LLM provider integration (LiteLLM, Ollama, GPT-OSS)

### **Domain-Specific Applications**
- **[Research Bot](./RESEARCH_BOT.md)** - Multi-agent research system with planning, search, and synthesis
- **[Customer Service](./CUSTOMER_SERVICE.md)** - Conversational workflows with escalation and state management
- **[Financial Research](./FINANCIAL_RESEARCH_AGENT.md)** - Complex multi-agent financial analysis system
- **[Reasoning Content](./REASONING_CONTENT.md)** - Accessing model reasoning and thought processes

## 🚀 **Getting Started**

### **Prerequisites**
- Temporal server [running locally](https://docs.temporal.io/cli/server#start-dev)
- Required dependencies: `uv sync --group openai-agents`
- OpenAI API key: `export OPENAI_API_KEY=your_key_here`

### **Quick Start**
1. **Choose a Service**: Start with [Basic Examples](./BASIC.md) for fundamental concepts
2. **Run the Worker**: Execute the appropriate `run_worker.py` script
3. **Execute Workflow**: Use the corresponding `run_*_workflow.py` script
4. **Explore Patterns**: Move to [Agent Patterns](./AGENT_PATTERNS.md) for advanced usage

### **Development Workflow**
```bash
# Start Temporal server
temporal server start-dev

# Install dependencies
uv sync --group openai-agents

# Run a specific example
uv run openai_agents/basic/run_worker.py
# In another terminal
uv run openai_agents/basic/run_hello_world_workflow.py
```

## 🔧 **Key Integration Features**

### **Temporal Workflow Decorators**
```python
@workflow.defn
class AgentWorkflow:
    @workflow.run
    async def run(self, input: str) -> str:
        # Agent execution logic
        pass
```

### **OpenAI Agents Plugin**
```python
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin

worker = Worker(
    client,
    task_queue="openai-agents-task-queue",
    plugins=[OpenAIAgentsPlugin()],
)
```

### **Agent Integration (Implicit Activities)**
```python
from agents import Agent, Runner

agent = Agent(name="MyAgent", instructions="...")
# This automatically creates a Temporal Activity under the hood
result = await Runner.run(agent, input_text)
```

## 📖 **Documentation Structure**

Each service documentation follows a consistent structure:
- **Introduction**: Service purpose and role in the ecosystem
- **Architecture**: System design and component relationships
- **Code Examples**: Implementation patterns with file paths and benefits
- **Development Guidelines**: Best practices and common patterns
- **File Organization**: Directory structure and file purposes

## 🔗 **Additional Resources**

- [Temporal Python SDK Documentation](https://docs.temporal.io/python)
- [OpenAI Agents SDK Documentation](https://github.com/openai/openai-agents-python)
- [Module Documentation](https://github.com/temporalio/sdk-python/blob/main/temporalio/contrib/openai_agents/README.md)
- [Temporal Blog: OpenAI Agents Integration](https://temporal.io/blog/announcing-openai-agents-sdk-integration)
- [Community Demos](https://github.com/temporal-community/openai-agents-demos)

## 🎯 **Use Cases**

This integration is ideal for:
- **Conversational AI**: Long-running, stateful conversations with memory
- **Multi-Agent Systems**: Coordinated AI agents working on complex tasks
- **Research & Analysis**: AI-powered research workflows with tool integration
- **Customer Service**: Intelligent support systems with escalation capabilities
- **Content Generation**: AI content creation with workflow orchestration
- **Data Processing**: AI-driven data analysis and transformation pipelines

---

*For detailed implementation examples and specific use cases, refer to the individual service documentation linked above.*
