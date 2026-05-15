import asyncio
from datetime import timedelta

from temporalio.client import Client
from temporalio.common import RetryPolicy
from temporalio.envconfig import ClientConfig

from activities import record_response
from models import TASK_QUEUE, SurveyResponse, SurveyResponseInput


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
    result = await client.execute_activity(
        record_response,
        input,
        id=f"survey-replay2026-{user_id}",
        task_queue=TASK_QUEUE,
        start_to_close_timeout=timedelta(seconds=180),
        heartbeat_timeout=timedelta(seconds=10),
        retry_policy=RetryPolicy(maximum_attempts=10),
    )
    print(f"Activity result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
