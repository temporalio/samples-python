import asyncio
import uuid
from pathlib import Path
from typing import Optional

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from sleep_for_days import TASK_QUEUE
from sleep_for_days.workflows import SleepForDaysWorkflow


async def main(client: Optional[Client] = None):
    if not client:
        # Get repo root - 1 level deep from root

        repo_root = Path(__file__).resolve().parent.parent

        config_file = repo_root / "temporal.toml"

        
        config = ClientConfig.load_client_connect_config(config_file=str(config_file))
        config["target_host"] = "localhost:7233"
        client = await Client.connect(**config)
    wf_handle = await client.start_workflow(
        SleepForDaysWorkflow.run,
        id=f"sleep-for-days-workflow-id-{uuid.uuid4()}",
        task_queue=TASK_QUEUE,
    )
    # Wait for workflow completion (runs indefinitely until it receives a signal)
    print(await wf_handle.result())


if __name__ == "__main__":
    asyncio.run(main())
