from datetime import timedelta
from typing import Optional

import pytest
from agents import ModelProvider, ModelResponse
from temporalio.contrib.openai_agents import (
    ModelActivityParameters,
    OpenAIAgentsPlugin,
    TestModel,
    TestModelProvider,
)


def sequential_test_model(responses: list[ModelResponse]) -> TestModel:
    responses = iter(responses)
    return TestModel(lambda: next(responses))


@pytest.fixture
def model_provider(test_model):
    return TestModelProvider(test_model)


@pytest.fixture
def plugins(model_provider: Optional[ModelProvider]):
    return [
        OpenAIAgentsPlugin(
            model_params=ModelActivityParameters(
                start_to_close_timeout=timedelta(seconds=30)
            ),
            model_provider=model_provider,
        )
    ]
