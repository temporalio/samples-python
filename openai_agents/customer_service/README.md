# Customer Service

Interactive customer service agent with escalation capabilities, extended with Temporal's durable conversational workflows.

*Adapted from [OpenAI Agents SDK customer service](https://github.com/openai/openai-agents-python/tree/main/examples/customer_service)*

This example demonstrates how to build persistent, stateful conversations where each conversation maintains state across multiple interactions and can survive system restarts and failures.

## Running the Example

First, start the worker:
```bash
uv run openai_agents/customer_service/run_worker.py
```

Then start a customer service conversation:
```bash
uv run openai_agents/customer_service/run_customer_service_client.py --conversation-id my-conversation-123
```

You can start a new conversation with any unique conversation ID, or resume existing conversations by using the same conversation ID. The conversation state is persisted in the Temporal workflow, allowing you to resume conversations even after restarting the client.