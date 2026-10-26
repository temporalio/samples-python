"""Offline tests for the OpenAI-compatible model provider sample."""

import uuid
from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Any

import pytest
from agents import (
    AgentOutputSchemaBase,
    Handoff,
    Model,
    ModelResponse,
    ModelSettings,
    ModelTracing,
    OpenAIChatCompletionsModel,
    Tool,
    TResponseInputItem,
)
from temporalio.client import Client
from temporalio.openai_agents import ModelActivityParameters, OpenAIAgentsPlugin
from temporalio.openai_agents.testing import ResponseBuilders, TestModelProvider
from temporalio.worker import Worker

from openai_agents.model_providers.openai_compatible_providers import (
    PROVIDERS,
    OpenAICompatibleModelProvider,
    OpenAICompatibleProvider,
)
from openai_agents.model_providers.workflows.openai_compatible_workflow import (
    OpenAICompatibleAgentWorkflow,
)


def test_provider_table() -> None:
    assert set(PROVIDERS) == {"baseten", "fireworks", "together"}
    for name, provider in PROVIDERS.items():
        assert provider.name == name
        assert provider.base_url.startswith("https://")
        assert provider.api_key_env.endswith("_API_KEY")
        assert provider.model


@pytest.mark.parametrize("provider", PROVIDERS.values(), ids=lambda p: p.name)
def test_model_provider_targets_the_endpoint(
    monkeypatch: pytest.MonkeyPatch, provider: OpenAICompatibleProvider
) -> None:
    monkeypatch.setenv(provider.api_key_env, "test-key")
    model_provider = OpenAICompatibleModelProvider(provider)

    default = model_provider.get_model(None)
    assert isinstance(default, OpenAIChatCompletionsModel)
    assert default.model == provider.model
    client = default._client
    assert str(client.base_url).rstrip("/") == provider.base_url
    assert client.api_key == "test-key"
    # Temporal owns retries: one HTTP call per Activity attempt.
    assert client.max_retries == 0

    override = model_provider.get_model("some/other-model")
    assert isinstance(override, OpenAIChatCompletionsModel)
    assert override.model == "some/other-model"


def test_model_provider_requires_the_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = PROVIDERS["together"]
    monkeypatch.delenv(provider.api_key_env, raising=False)
    with pytest.raises(KeyError, match=provider.api_key_env):
        OpenAICompatibleModelProvider(provider)


class RecordingModel(Model):
    """Scripted model that records the settings each call was made with."""

    def __init__(self, responses: list[ModelResponse]) -> None:
        self._responses = iter(responses)
        self.settings: list[ModelSettings] = []

    async def get_response(
        self,
        system_instructions: str | None,
        input: str | list[TResponseInputItem],
        model_settings: ModelSettings,
        tools: list[Tool],
        output_schema: AgentOutputSchemaBase | None,
        handoffs: list[Handoff],
        tracing: ModelTracing,
        **kwargs: Any,
    ) -> ModelResponse:
        self.settings.append(model_settings)
        return next(self._responses)

    async def stream_response(self, *args: Any, **kwargs: Any) -> AsyncIterator[Any]:
        raise NotImplementedError
        yield


async def test_workflow_uses_the_tool_and_the_default_model(client: Client) -> None:
    # The Workflow names no model, so the provider's default is used; a
    # scripted model stands in for the provider here.
    model = RecordingModel(
        [
            ResponseBuilders.tool_call('{"city": "Tokyo"}', "get_weather"),
            ResponseBuilders.output_message("Sunny over Tokyo"),
        ]
    )
    config = client.config()
    config["plugins"] = [
        *config["plugins"],
        OpenAIAgentsPlugin(
            model_params=ModelActivityParameters(
                start_to_close_timeout=timedelta(seconds=30)
            ),
            model_provider=TestModelProvider(model),
        ),
    ]
    client = Client(**config)
    task_queue = f"openai-agents-openai-compatible-{uuid.uuid4()}"

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[OpenAICompatibleAgentWorkflow],
    ):
        result = await client.execute_workflow(
            OpenAICompatibleAgentWorkflow.run,
            "What's the weather in Tokyo?",
            id=f"openai-compatible-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert result == "Sunny over Tokyo"
    # The Agents SDK's defaults for OpenAI's default model (a reasoning effort
    # and verbosity) must not reach a provider that rejects them.
    assert len(model.settings) == 2
    for settings in model.settings:
        assert settings.reasoning is None
        assert settings.verbosity is None
