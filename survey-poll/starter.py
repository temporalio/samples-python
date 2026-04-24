import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from models import TASK_QUEUE, SurveyResponse, SurveyResponseInput
from workflows import SurveyResponseWorkflow


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    client = await Client.connect(**config)
    print("Connected to Temporal Service")

    user_id = "demo-user-001"
    input = SurveyResponseInput(
        user_id=user_id,
        response=SurveyResponse.YES,
        comment="Looking forward to it",
    )
    result = await client.execute_workflow(
        SurveyResponseWorkflow.run,
        input,
        id=f"survey-replay2026-{user_id}",
        task_queue=TASK_QUEUE,
    )
    print(f"Workflow result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
