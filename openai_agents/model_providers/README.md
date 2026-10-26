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

#### OpenRouter
Uses [OpenRouter](https://openrouter.ai/) as the model provider, so the agent can run on any of the hundreds of models OpenRouter serves through one API key. OpenRouter speaks the OpenAI Chat Completions API, so the stock `OpenAIProvider` works once it is pointed at OpenRouter's base URL.

Start the OpenRouter worker:
```bash
export OPENROUTER_API_KEY="your_openrouter_api_key"

uv run openai_agents/model_providers/run_openrouter_worker.py
```

Then run the example in a separate terminal:
```bash
uv run openai_agents/model_providers/run_openrouter_workflow.py
```

The workflow uses `openrouter/auto`, so OpenRouter picks a model per request; change `OPENROUTER_MODEL` in [workflows/openrouter_workflow.py](workflows/openrouter_workflow.py) to pin any OpenRouter model slug. Tools that run inside the Workflow must be `async`: the Agents SDK runs sync tools in a thread, which the Workflow sandbox does not allow. See the [openrouter](../../openrouter) sample for calling OpenRouter directly from Activities with cost tracking and budgets.

#### Open-weight models on Baseten, Fireworks AI, and Together AI
[Baseten](https://www.baseten.co/), [Fireworks AI](https://fireworks.ai/), and [Together AI](https://www.together.ai/) serve open-weight models behind the OpenAI Chat Completions API, so one Worker script covers all three. It points the OpenAI client at the provider's base URL and supplies a default model; the Workflow names no model, so the same Workflow runs on whichever provider the Worker was started with.

| Provider | API key | Default model |
|---|---|---|
| Baseten | `BASETEN_API_KEY` | `openai/gpt-oss-120b` |
| Fireworks AI | `FIREWORKS_API_KEY` | `accounts/fireworks/models/gpt-oss-120b` |
| Together AI | `TOGETHER_API_KEY` | `openai/gpt-oss-120b` |

Start the worker for one provider (`baseten`, `fireworks`, or `together`):
```bash
export TOGETHER_API_KEY="your_together_api_key"

uv run openai_agents/model_providers/run_openai_compatible_worker.py --provider together
```

Then run the example in a separate terminal:
```bash
uv run openai_agents/model_providers/run_openai_compatible_workflow.py
```

The providers are defined in [openai_compatible_providers.py](openai_compatible_providers.py). Add another OpenAI-compatible endpoint by appending to `PROVIDERS`, or run an agent on a different model by setting `model=` on the `Agent`. Tools that run inside the Workflow must be `async`: the Agents SDK runs sync tools in a thread, which the Workflow sandbox does not allow. The Temporal docs have a page per provider: [Baseten](https://docs.temporal.io/develop/python/integrations/baseten), [Fireworks AI](https://docs.temporal.io/develop/python/integrations/fireworks-ai), and [Together AI](https://docs.temporal.io/develop/python/integrations/together-ai).

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
- **Custom Example Provider** - Custom ModelProvider pattern
- **LiteLLM Provider** - Interactive model/API key input