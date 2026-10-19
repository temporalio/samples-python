import asyncio
import logging

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from openrouter.activities import OpenRouterActivities, build_client
from openrouter.budget_gate.workflow import BudgetGateWorkflow
from openrouter.shared import BUDGET_GATE_TASK_QUEUE


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    activities = OpenRouterActivities(build_client())

    worker = Worker(
        client,
        task_queue=BUDGET_GATE_TASK_QUEUE,
        workflows=[BudgetGateWorkflow],
        activities=[activities.call_openrouter],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
