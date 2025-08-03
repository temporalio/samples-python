# Agent Patterns

Common agentic patterns extended with Temporal's durable execution capabilities.

*Adapted from [OpenAI Agents SDK agent patterns](https://github.com/openai/openai-agents-python/tree/main/examples/agent_patterns)*

Before running these examples, be sure to review the [prerequisites and background on the integration](../README.md).

## Running the Examples

First, start the worker (supports all patterns):
```bash
uv run openai_agents/agent_patterns/run_worker.py
```

Then run individual examples in separate terminals:

### Deterministic Flows
Sequential agent execution with validation gates - demonstrates breaking complex tasks into smaller steps:
```bash
uv run openai_agents/agent_patterns/run_deterministic_workflow.py
```

### Parallelization
Run multiple agents in parallel and select the best result - useful for improving quality or reducing latency:
```bash
uv run openai_agents/agent_patterns/run_parallelization_workflow.py
```

### LLM-as-a-Judge
Iterative improvement using feedback loops - generate content, evaluate it, and improve until satisfied:
```bash
uv run openai_agents/agent_patterns/run_llm_as_a_judge_workflow.py
```

### Agents as Tools
Use agents as callable tools within other agents - enables composition and specialized task delegation:
```bash
uv run openai_agents/agent_patterns/run_agents_as_tools_workflow.py
```

### Agent Routing and Handoffs
Route requests to specialized agents based on content analysis (adapted for non-streaming):
```bash
uv run openai_agents/agent_patterns/run_routing_workflow.py
```

### Input Guardrails
Pre-execution validation to prevent unwanted requests - demonstrates safety mechanisms:
```bash
uv run openai_agents/agent_patterns/run_input_guardrails_workflow.py
```

### Output Guardrails
Post-execution validation to detect sensitive content - ensures safe responses:
```bash
uv run openai_agents/agent_patterns/run_output_guardrails_workflow.py
```

### Forcing Tool Use
Control tool execution strategies - choose between different approaches to tool usage:
```bash
uv run openai_agents/agent_patterns/run_forcing_tool_use_workflow.py
```

## Pattern Details

### Deterministic Flows
A common tactic is to break down a task into a series of smaller steps. Each task can be performed by an agent, and the output of one agent is used as input to the next. For example, if your task was to generate a story, you could break it down into the following steps:

1. Generate an outline
2. Check outline quality and genre
3. Write the story (only if outline passes validation)

Each of these steps can be performed by an agent. The output of one agent is used as input to the next.

### Parallelization
Running multiple agents in parallel is a common pattern. This can be useful for both latency (e.g. if you have multiple steps that don't depend on each other) and also for other reasons e.g. generating multiple responses and picking the best one.

### LLM-as-a-Judge
LLMs can often improve the quality of their output if given feedback. A common pattern is to generate a response using a model, and then use a second model to provide feedback. You can even use a small model for the initial generation and a larger model for the feedback, to optimize cost.

### Agents as Tools
The mental model for handoffs is that the new agent "takes over". It sees the previous conversation history, and owns the conversation from that point onwards. However, this is not the only way to use agents. You can also use agents as a tool - the tool agent goes off and runs on its own, and then returns the result to the original agent.

### Guardrails
Related to parallelization, you often want to run input guardrails to make sure the inputs to your agents are valid. For example, if you have a customer support agent, you might want to make sure that the user isn't trying to ask for help with a math problem.

You can definitely do this without any special Agents SDK features by using parallelization, but we support a special guardrail primitive. Guardrails can have a "tripwire" - if the tripwire is triggered, the agent execution will immediately stop and a `GuardrailTripwireTriggered` exception will be raised.

This is really useful for latency: for example, you might have a very fast model that runs the guardrail and a slow model that runs the actual agent. You wouldn't want to wait for the slow model to finish, so guardrails let you quickly reject invalid inputs.

## Omitted Examples

The following patterns from the [reference repository](https://github.com/openai/openai-agents-python/tree/main/examples/agent_patterns) are not included in this Temporal adaptation:

- **Streaming Guardrails**: Requires streaming capabilities which are not yet available in the Temporal integration