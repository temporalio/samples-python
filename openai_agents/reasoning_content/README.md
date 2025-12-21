# Reasoning Content

Example demonstrating how to use the reasoning content feature with models that support it, running in the context of Temporal's durable execution.

*Adapted from [OpenAI Agents SDK reasoning content](https://github.com/openai/openai-agents-python/tree/main/examples/reasoning_content)*

## Overview

Some models, like deepseek-reasoner, provide a reasoning_content field in addition to the regular content. This example shows how to access and use this reasoning content within Temporal workflows. The reasoning content contains the model's step-by-step thinking process before providing the final answer.

## Architecture

This example uses an activity to handle the OpenAI model calls. The workflow orchestrates the process by calling the `get_reasoning_response` activity, which uses the OpenAI provider to get a response from a reasoning-capable model and extracts both reasoning content and regular content.

The model calls are run in an activity rather than directly in the workflow because Temporal's the involve I/O.

## Running the Example

First, start the worker:
```bash
uv run openai_agents/reasoning_content/run_worker.py
```

Then run the reasoning content workflow:
```bash
uv run openai_agents/reasoning_content/run_reasoning_content_workflow.py
```

## Requirements

- Set your `OPENAI_API_KEY` environment variable
- Use a model that supports reasoning content (e.g., `deepseek-reasoner`)
- Optionally set `EXAMPLE_MODEL_NAME` environment variable to specify the model

## Note on Streaming

The original OpenAI Agents SDK example includes streaming capabilities, but since Temporal workflows do not support streaming yet, this example contains only the non-streaming approach.