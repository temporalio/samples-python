# Multi-Agent Systems

Samples demonstrating multi-agent orchestration patterns with LangGraph and Temporal.

## Samples

### [Supervisor](./supervisor/)

A supervisor agent that coordinates specialized worker agents (researcher, writer, analyst). The supervisor routes tasks to appropriate agents and aggregates results.

**Demonstrates:**
- Multi-agent orchestration patterns
- Supervisor decision-making and task routing
- Agent specialization with different tools
- Durable execution across agent handoffs

## Multi-Agent Patterns

LangGraph supports several multi-agent patterns:

1. **Supervisor** (this sample): A central coordinator routes tasks to specialists
2. **Swarm**: Agents hand off to each other dynamically based on the conversation
3. **Hierarchical**: Team supervisors under a top-level coordinator
4. **Collaborative**: Agents work together on shared state

## Temporal Benefits for Multi-Agent Systems

Running multi-agent systems with Temporal provides:

- **Durability**: Agent interactions are checkpointed, surviving failures
- **Retries**: Failed agent calls are automatically retried
- **Visibility**: Track complex agent interactions through Temporal's UI
- **Long-running support**: Multi-agent workflows can run for extended periods
- **Scalability**: Distribute agent execution across workers
