import asyncio
import logging
from datetime import datetime
from ipaddress import IPv4Address
from pathlib import Path

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.envconfig import ClientConfig

from pydantic_converter.worker import MyPydanticModel, MyWorkflow


async def main():
    logging.basicConfig(level=logging.INFO)
    
    # Get repo root - 1 level deep from root

    
    repo_root = Path(__file__).resolve().parent.parent

    
    config_file = repo_root / "temporal.toml"

    
    
    config = ClientConfig.load_client_connect_config(config_file=str(config_file))
    config["target_host"] = "localhost:7233"
    # Connect client using the Pydantic converter
    config["data_converter"] = pydantic_data_converter
    
    client = await Client.connect(**config)

    # Run workflow
    result = await client.execute_workflow(
        MyWorkflow.run,
        [
            MyPydanticModel(
                some_ip=IPv4Address("127.0.0.1"),
                some_date=datetime(2000, 1, 2, 3, 4, 5),
            ),
            MyPydanticModel(
                some_ip=IPv4Address("127.0.0.2"),
                some_date=datetime(2001, 2, 3, 4, 5, 6),
            ),
        ],
        id="pydantic_converter-workflow-id",
        task_queue="pydantic_converter-task-queue",
    )
    logging.info("Got models from client: %s" % result)


if __name__ == "__main__":
    asyncio.run(main())
