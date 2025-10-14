from datetime import timedelta

import pytest
from temporalio.contrib.openai_agents import ModelActivityParameters, OpenAIAgentsPlugin


@pytest.fixture
def model_provider():
    return None
