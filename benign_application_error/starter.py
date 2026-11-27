import asyncio
import logging
from pythonjsonlogger import json
from temporalio.client import Client
from benign_application_error.worker import set_init_runtime
from benign_application_error.workflow import BenignApplicationErrorWorkflow


async def main():
    runtime = set_init_runtime()

    client = await Client.connect(
        "localhost:7233",
        runtime=runtime,
    )

    # BENIGN=True
    try:
        await client.execute_workflow(
            BenignApplicationErrorWorkflow.run,
            True,
            id="benign_application_error-wf-1",
            task_queue="benign_application_error_task_queue",
        )
    except Exception as e:
        logging.debug(f"BENIGN=True run finished with exception: {e}")

    # BENIGN=False
    try:
        await client.execute_workflow(
            BenignApplicationErrorWorkflow.run,
            False,
            id="benign_application_error-wf-2",
            task_queue="benign_application_error_task_queue",
        )
    except Exception as e:
        logging.debug(f"BENIGN=False run finished with exception: {e}")



if __name__ == "__main__":
    asyncio.run(main())
