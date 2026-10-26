"""Open-weight model providers with OpenAI-compatible APIs.

Baseten, Fireworks AI, and Together AI all serve open-weight models behind the
OpenAI Chat Completions API, so the stock ``openai`` client reaches them once
it is pointed at the provider's base URL. The Workflow is the same for all of
them; the Worker chooses the provider and the default model.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from agents import Model, ModelProvider, OpenAIChatCompletionsModel
from openai import AsyncOpenAI


@dataclass(frozen=True)
class OpenAICompatibleProvider:
    """An OpenAI-compatible inference endpoint and a default model on it."""

    name: str
    base_url: str
    api_key_env: str
    # A model with tool-calling support, in the provider's naming scheme.
    model: str


# @@@SNIPSTART python-openai-agents-baseten-provider
BASETEN = OpenAICompatibleProvider(
    name="baseten",
    base_url="https://inference.baseten.co/v1",
    api_key_env="BASETEN_API_KEY",
    model="openai/gpt-oss-120b",
)
# @@@SNIPEND

# @@@SNIPSTART python-openai-agents-fireworks-provider
FIREWORKS = OpenAICompatibleProvider(
    name="fireworks",
    base_url="https://api.fireworks.ai/inference/v1",
    api_key_env="FIREWORKS_API_KEY",
    model="accounts/fireworks/models/gpt-oss-120b",
)
# @@@SNIPEND

# @@@SNIPSTART python-openai-agents-together-provider
TOGETHER = OpenAICompatibleProvider(
    name="together",
    base_url="https://api.together.ai/v1",
    api_key_env="TOGETHER_API_KEY",
    model="openai/gpt-oss-120b",
)
# @@@SNIPEND

PROVIDERS: dict[str, OpenAICompatibleProvider] = {
    provider.name: provider for provider in (BASETEN, FIREWORKS, TOGETHER)
}


# @@@SNIPSTART python-openai-agents-openai-compatible-model-provider
class OpenAICompatibleModelProvider(ModelProvider):
    """OpenAI Agents SDK model provider for an OpenAI-compatible endpoint.

    Client retries are off: the Temporal plugin runs each model call as an
    Activity, and the Activity's Retry Policy owns the retries. An agent that
    names no model gets the provider's default; an agent can name any other
    model the provider serves.
    """

    def __init__(self, provider: OpenAICompatibleProvider) -> None:
        self._provider = provider
        self._client = AsyncOpenAI(
            base_url=provider.base_url,
            api_key=os.environ[provider.api_key_env],
            max_retries=0,
        )

    def get_model(self, model_name: str | None) -> Model:
        # Chat Completions is the API all of these providers serve. The Agents
        # SDK defaults to the Responses API, which not every provider offers.
        return OpenAIChatCompletionsModel(
            model=model_name or self._provider.model,
            openai_client=self._client,
        )


# @@@SNIPEND
