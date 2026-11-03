"""Open-weight model providers with OpenAI-compatible APIs.

Baseten, Fireworks AI, and Together AI all serve open-weight models behind the
OpenAI Chat Completions API, so the stock ``openai`` client reaches them once
it is pointed at the provider's base URL. One Worker serves every provider
whose API key is set, and each Workflow picks a provider through the model
name it gives its agent: ``<provider>/<model>``, such as
``together/openai/gpt-oss-120b``.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass

from agents import Model, ModelProvider, OpenAIChatCompletionsModel
from openai import AsyncOpenAI
from temporalio.exceptions import ApplicationError


@dataclass(frozen=True)
class OpenAICompatibleProvider:
    """An OpenAI-compatible inference endpoint and an example model on it."""

    # The prefix that selects this provider in a model name.
    name: str
    base_url: str
    api_key_env: str
    # A model with tool-calling support, in the provider's naming scheme. The
    # starter runs it when no model is given.
    default_model: str


# @@@SNIPSTART python-openai-agents-baseten-provider
BASETEN = OpenAICompatibleProvider(
    name="baseten",
    base_url="https://inference.baseten.co/v1",
    api_key_env="BASETEN_API_KEY",
    default_model="openai/gpt-oss-120b",
)
# @@@SNIPEND

# @@@SNIPSTART python-openai-agents-fireworks-provider
FIREWORKS = OpenAICompatibleProvider(
    name="fireworks",
    base_url="https://api.fireworks.ai/inference/v1",
    api_key_env="FIREWORKS_API_KEY",
    default_model="accounts/fireworks/models/gpt-oss-120b",
)
# @@@SNIPEND

# @@@SNIPSTART python-openai-agents-together-provider
TOGETHER = OpenAICompatibleProvider(
    name="together",
    base_url="https://api.together.ai/v1",
    api_key_env="TOGETHER_API_KEY",
    default_model="openai/gpt-oss-120b",
)
# @@@SNIPEND

PROVIDERS: dict[str, OpenAICompatibleProvider] = {
    provider.name: provider for provider in (BASETEN, FIREWORKS, TOGETHER)
}


# @@@SNIPSTART python-openai-agents-openai-compatible-model-provider
class OpenAICompatibleModelProvider(ModelProvider):
    """Routes ``<provider>/<model>`` names to the matching OpenAI-compatible endpoint.

    One Worker serves every provider whose API key is set, so Workflows on
    different providers run side by side on the same Task Queue. Client
    retries are off: the plugin runs each model call as a Temporal Activity,
    and the Activity's Retry Policy owns the retries.
    """

    def __init__(self, providers: Iterable[OpenAICompatibleProvider]) -> None:
        self._providers = {provider.name: provider for provider in providers}
        self._clients: dict[str, AsyncOpenAI] = {}
        for provider in self._providers.values():
            api_key = os.environ.get(provider.api_key_env)
            if api_key:
                self._clients[provider.name] = AsyncOpenAI(
                    base_url=provider.base_url, api_key=api_key, max_retries=0
                )

    @property
    def configured(self) -> list[str]:
        """Names of the providers whose API key is set."""
        return sorted(self._clients)

    def get_model(self, model_name: str | None) -> Model:
        provider_name, _, model = (model_name or "").partition("/")
        provider = self._providers.get(provider_name)
        if provider is None or not model:
            # A mistake in the Workflow's input: fail the Activity without retrying.
            raise ApplicationError(
                f"Model name {model_name!r} must be <provider>/<model> with a "
                f"provider in {sorted(self._providers)}",
                non_retryable=True,
            )
        client = self._clients.get(provider_name)
        if client is None:
            raise ApplicationError(
                f"Set {provider.api_key_env} and restart the Worker to use {provider_name}",
                non_retryable=True,
            )
        # Chat Completions is the API all of these providers serve. The Agents
        # SDK defaults to the Responses API, which not every provider offers.
        return OpenAIChatCompletionsModel(model=model, openai_client=client)


# @@@SNIPEND
