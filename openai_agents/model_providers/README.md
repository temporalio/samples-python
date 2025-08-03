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

uv run openai_agents/model_providers/run_worker_litellm_provider.py
```

Then run the example in a separate terminal:
```bash
uv run openai_agents/model_providers/run_litellm_auto_workflow.py
```

The example uses Anthropic Claude by default but can be modified to use other LiteLLM-supported providers.

Find more LiteLLM providers at: https://docs.litellm.ai/docs/providers

## Not Yet Implemented

- **Custom Example Agent** - Custom OpenAI client integration
- **Custom Example Global** - Global default client configuration  
- **Custom Example Provider** - Custom ModelProvider pattern
- **LiteLLM Provider** - Interactive model/API key input