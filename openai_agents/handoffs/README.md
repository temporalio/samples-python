# Handoffs Examples

Agent handoff patterns with message filtering in Temporal workflows.

*Adapted from [OpenAI Agents SDK handoffs examples](https://github.com/openai/openai-agents-python/tree/main/examples/handoffs)*

Before running these examples, be sure to review the [prerequisites and background on the integration](../README.md).

## Running the Examples

First, start the worker:
```bash
uv run openai_agents/handoffs/run_worker.py
```

Then run the workflow:

### Message Filter Workflow
Demonstrates agent handoffs with message history filtering:
```bash
uv run openai_agents/handoffs/run_message_filter_workflow.py
```

## Workflow Pattern

The workflow demonstrates a 4-step conversation with message filtering:

1. **Introduction**: User greets first agent with name
2. **Tool Usage**: First agent generates random number using function tool
3. **Agent Switch**: Conversation moves to second agent for general questions
4. **Spanish Handoff**: Second agent detects Spanish and hands off to Spanish specialist

During the Spanish handoff, message filtering occurs:
- All tool-related messages are removed from history
- First two messages are dropped (demonstration of selective context)
- Filtered conversation continues with Spanish agent

The workflow returns both the final response and complete message history for inspection.

## Omitted Examples

The following patterns from the [reference repository](https://github.com/openai/openai-agents-python/tree/main/examples/handoffs) are not included in this Temporal adaptation:

- **Message Filter Streaming**: Streaming capabilities are not yet available in the Temporal integration