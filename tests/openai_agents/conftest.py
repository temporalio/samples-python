from datetime import timedelta
from typing import Optional

import pytest
from agents import Model, ModelProvider
from temporalio.contrib.openai_agents import ModelActivityParameters, OpenAIAgentsPlugin


class MockedModelProvider(ModelProvider):
    def __init__(self, mocked_model):
        self.mocked_model = mocked_model

    def get_model(self, model_name: str | None) -> Model:
        return self.mocked_model


@pytest.fixture
def model_provider(mocked_model):
    return MockedModelProvider(mocked_model)


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
