import uuid
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.contrib.openai_agents.testing import (
    AgentEnvironment,
    ResponseBuilders,
    TestModel,
)
from temporalio.worker import Worker

from openai_agents.basic.workflows.non_strict_output_workflow import (
    NonStrictOutputWorkflow,
)


def non_strict_output_test_model():
    # NOTE: AgentOutputSchema (used in the workflow definition), has a schema where the outer
    # object must be "response". Therefore, mocked model responses must use "response", just as the real model does. 
    return TestModel.returning_responses(
        [
            ResponseBuilders.output_message(
                '{"response": {"jokes": {"1": "Why do programmers prefer dark mode? Because light attracts bugs!", "2": "How many programmers does it take to change a light bulb? None, that\'s a hardware problem.", "3": "Why do Java developers wear glasses? Because they can\'t C#!"}}}'
            )
        ]
    )


async def test_execute_workflow(client: Client):
    task_queue_name = str(uuid.uuid4())

    async with AgentEnvironment(model=non_strict_output_test_model()) as agent_env:
        client = agent_env.applied_on_client(client)
        async with Worker(
            client,
            task_queue=task_queue_name,
            workflows=[NonStrictOutputWorkflow],
            activity_executor=ThreadPoolExecutor(5),
            # No external activities needed
        ):
            result = await client.execute_workflow(
                NonStrictOutputWorkflow.run,
                "Tell me 3 funny jokes about programming.",
                id=str(uuid.uuid4()),
                task_queue=task_queue_name,
            )

            # Verify the result has the expected structure
            assert isinstance(result, dict)

            assert "strict_error" in result
            assert "non_strict_result" in result

            # If there's a strict_error, it should be a string
            if "strict_error" in result:
                assert isinstance(result["strict_error"], str)
                assert len(result["strict_error"]) > 0

            jokes = result["non_strict_result"]["jokes"]
            assert isinstance(jokes, dict)
            assert isinstance(jokes[list(jokes.keys())[0]], str)
