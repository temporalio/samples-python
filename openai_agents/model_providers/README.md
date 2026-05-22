# Model Providers Examples

Custom LLM provider integration examples for OpenAI Agents SDK with Temporal workflows.

*Adapted from [OpenAI Agents SDK model providers examples](https://github.com/openai/openai-agents-python/tree/main/examples/model_providers)*

Before running these examples, be sure to review the [prerequisites and background on the integration](../README.md).

## Running the Examples

### Currently Implemented

#### LiteLLM Auto
Uses built-in LiteLLM support to connect to various model providers.

Start the LiteLLM provider worker:
```bash
# Set the required environment variable for your chosen provider
export ANTHROPIC_API_KEY="your_anthropic_api_key"  # For Anthropic

uv run openai_agents/model_providers/run_litellm_provider_worker.py
```

Then run the example in a separate terminal:
```bash
uv run openai_agents/model_providers/run_litellm_auto_workflow.py
```

The example uses Anthropic Claude by default but can be modified to use other LiteLLM-supported providers.

Find more LiteLLM providers at: https://docs.litellm.ai/docs/providers

#### Tuning Engines
Uses a custom `ModelProvider` to route OpenAI Agents SDK model calls through the Tuning Engines OpenAI-compatible gateway.

Set your Tuning Engines inference key and, optionally, the tenant model alias to use:

```bash
export TUNING_ENGINES_API_KEY="sk-te-..."
export TUNING_ENGINES_MODEL="your-model-alias"
# Optional, defaults to https://api.tuningengines.com/v1
export TUNING_ENGINES_BASE_URL="https://api.tuningengines.com/v1"
```

Start the Tuning Engines provider worker:

```bash
uv run openai_agents/model_providers/run_tuning_engines_worker.py
```

Then run the example in a separate terminal:

```bash
uv run openai_agents/model_providers/run_tuning_engines_workflow.py
```

Use a model alias that is available to the configured Tuning Engines inference key.

### Extra

#### GPT-OSS with Ollama

This example demonstrates tool calling using the gpt-oss reasoning model with a local Ollama server.
Running this example requires sufficiently powerful hardware (and involves a  14 GB model download.
It is adapted from the [OpenAI Cookbook example](https://cookbook.openai.com/articles/gpt-oss/run-locally-ollama#agents-sdk-integration).


Make sure you have [Ollama](https://ollama.com/) installed:
```bash
ollama serve
```

Download the `gpt-oss` model:
```bash
ollama pull gpt-oss:20b
```

Start the gpt-oss worker:
```bash
uv run openai_agents/model_providers/run_gpt_oss_worker.py
```

Then run the example in a separate terminal:
```bash
uv run openai_agents/model_providers/run_gpt_oss_workflow.py
```

### Not Yet Implemented

- **Custom Example Agent** - Custom OpenAI client integration
- **Custom Example Global** - Global default client configuration  
- **LiteLLM Provider** - Interactive model/API key input
