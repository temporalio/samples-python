"""Offline tests for the OpenAI-compatible model provider sample."""

import asyncio
import uuid
from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Any

import pytest
from agents import (
    AgentOutputSchemaBase,
    Handoff,
    Model,
    ModelProvider,
    ModelResponse,
    ModelSettings,
    ModelTracing,
    OpenAIChatCompletionsModel,
    Tool,
    TResponseInputItem,
)
from agents.items import TResponseStreamEvent
from temporalio.client import Client, WorkflowFailureError
from temporalio.exceptions import ActivityError, ApplicationError, RetryState
from temporalio.openai_agents import ModelActivityParameters, OpenAIAgentsPlugin
from temporalio.openai_agents.testing import ResponseBuilders
from temporalio.worker import Worker

from openai_agents.model_providers.openai_compatible_providers import (
    PROVIDERS,
    OpenAICompatibleModelProvider,
)
from openai_agents.model_providers.workflows.openai_compatible_workflow import (
    OpenAICompatibleAgentInput,
    OpenAICompatibleAgentWorkflow,
)

TOGETHER_MODEL = "together/openai/gpt-oss-120b"
FIREWORKS_MODEL = "fireworks/accounts/fireworks/models/gpt-oss-120b"


def test_provider_table() -> None:
    assert set(PROVIDERS) == {"baseten", "fireworks", "together"}
    for name, provider in PROVIDERS.items():
        assert provider.name == name
        assert "/" not in name
        assert provider.base_url.startswith("https://")
        assert provider.api_key_env.endswith("_API_KEY")
        assert provider.default_model


def _provider_with_keys(
    monkeypatch: pytest.MonkeyPatch, *names: str
) -> OpenAICompatibleModelProvider:
    for provider in PROVIDERS.values():
        monkeypatch.delenv(provider.api_key_env, raising=False)
    for name in names:
        monkeypatch.setenv(PROVIDERS[name].api_key_env, f"{name}-test-key")
    return OpenAICompatibleModelProvider(PROVIDERS.values())


def test_routes_a_prefixed_model_name_to_its_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model_provider = _provider_with_keys(monkeypatch, "together", "fireworks")
    assert model_provider.configured == ["fireworks", "together"]

    model = model_provider.get_model(TOGETHER_MODEL)
    assert isinstance(model, OpenAIChatCompletionsModel)
    assert model.model == "openai/gpt-oss-120b"
    client = model._client
    assert str(client.base_url).rstrip("/") == PROVIDERS["together"].base_url
    assert client.api_key == "together-test-key"
    # Temporal owns retries: one HTTP call per Activity attempt.
    assert client.max_retries == 0

    fireworks = model_provider.get_model(FIREWORKS_MODEL)
    assert isinstance(fireworks, OpenAIChatCompletionsModel)
    assert fireworks.model == "accounts/fireworks/models/gpt-oss-120b"
    assert (
        str(fireworks._client.base_url).rstrip("/") == PROVIDERS["fireworks"].base_url
    )


@pytest.mark.parametrize(
    "model_name", [None, "openai/gpt-oss-120b", "nope/model", "together", "together/"]
)
def test_rejects_a_name_without_a_known_provider_without_retrying(
    monkeypatch: pytest.MonkeyPatch, model_name: str | None
) -> None:
    model_provider = _provider_with_keys(monkeypatch, "together")
    with pytest.raises(ApplicationError) as err:
        model_provider.get_model(model_name)
    assert err.value.non_retryable


def test_rejects_a_provider_without_a_key_without_retrying(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model_provider = _provider_with_keys(monkeypatch, "together")
    with pytest.raises(ApplicationError, match="FIREWORKS_API_KEY") as err:
        model_provider.get_model(FIREWORKS_MODEL)
    assert err.value.non_retryable


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

    def stream_response(
        self, *args: Any, **kwargs: Any
    ) -> AsyncIterator[TResponseStreamEvent]:
        raise NotImplementedError()


class RecordingProvider(ModelProvider):
    """Stands in for the endpoints: one scripted model per model name."""

    def __init__(self, scripts: dict[str, list[ModelResponse]]) -> None:
        self.models = {name: RecordingModel(script) for name, script in scripts.items()}
        self.requested: list[str | None] = []

    def get_model(self, model_name: str | None) -> Model:
        self.requested.append(model_name)
        return self.models[model_name or ""]


def _script(answer: str) -> list[ModelResponse]:
    return [
        ResponseBuilders.tool_call('{"city": "Tokyo"}', "get_weather"),
        ResponseBuilders.output_message(answer),
    ]


def _with_provider(client: Client, provider: ModelProvider) -> Client:
    config = client.config()
    config["plugins"] = [
        *config["plugins"],
        OpenAIAgentsPlugin(
            model_params=ModelActivityParameters(
                start_to_close_timeout=timedelta(seconds=30)
            ),
            model_provider=provider,
        ),
    ]
    return Client(**config)


async def test_workflows_on_different_providers_share_one_worker(
    client: Client,
) -> None:
    provider = RecordingProvider(
        {
            TOGETHER_MODEL: _script("Sunny over Tokyo"),
            FIREWORKS_MODEL: _script("Clear Tokyo sky"),
        }
    )
    client = _with_provider(client, provider)
    task_queue = f"openai-agents-openai-compatible-{uuid.uuid4()}"

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[OpenAICompatibleAgentWorkflow],
    ):
        results = await asyncio.gather(
            *(
                client.execute_workflow(
                    OpenAICompatibleAgentWorkflow.run,
                    OpenAICompatibleAgentInput(
                        prompt="What's the weather in Tokyo?", model=model
                    ),
                    id=f"openai-compatible-{uuid.uuid4()}",
                    task_queue=task_queue,
                )
                for model in (TOGETHER_MODEL, FIREWORKS_MODEL)
            )
        )

    assert results == ["Sunny over Tokyo", "Clear Tokyo sky"]
    # Each Workflow's two model calls (the tool-call turn and the answer) were
    # routed by its own model name.
    assert sorted(provider.requested, key=str) == sorted(
        [TOGETHER_MODEL, TOGETHER_MODEL, FIREWORKS_MODEL, FIREWORKS_MODEL]
    )
    for model in provider.models.values():
        assert len(model.settings) == 2
        for settings in model.settings:
            # The agent names its model, so the Agents SDK sends none of the
            # settings meant for OpenAI's default model.
            assert settings.reasoning is None
            assert settings.verbosity is None


async def test_a_provider_without_a_key_fails_the_workflow_without_retrying(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _with_provider(client, _provider_with_keys(monkeypatch, "together"))
    task_queue = f"openai-agents-openai-compatible-{uuid.uuid4()}"

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[OpenAICompatibleAgentWorkflow],
    ):
        with pytest.raises(WorkflowFailureError) as err:
            await client.execute_workflow(
                OpenAICompatibleAgentWorkflow.run,
                OpenAICompatibleAgentInput(prompt="Hello", model=FIREWORKS_MODEL),
                id=f"openai-compatible-{uuid.uuid4()}",
                task_queue=task_queue,
            )

    activity_error = err.value.cause
    assert isinstance(activity_error, ActivityError)
    assert activity_error.retry_state == RetryState.NON_RETRYABLE_FAILURE
    assert isinstance(activity_error.cause, ApplicationError)
    assert "FIREWORKS_API_KEY" in activity_error.cause.message
