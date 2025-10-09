from datetime import timedelta

import pytest
from temporalio.contrib.openai_agents import ModelActivityParameters, OpenAIAgentsPlugin


@pytest.fixture(scope="session")
def plugins():
    return [
        OpenAIAgentsPlugin(
            model_params=ModelActivityParameters(
                start_to_close_timeout=timedelta(seconds=30)
            )
        )
    ]
