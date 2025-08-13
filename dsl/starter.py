import asyncio
import logging
import sys
import uuid

import dacite
import yaml
from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile

from dsl.workflow import DSLInput, DSLWorkflow


async def main(dsl_yaml: str) -> None:
    # Convert the YAML to our dataclass structure. We use PyYAML + dacite to do
    # this but it can be done any number of ways.
    dsl_input = dacite.from_dict(DSLInput, yaml.safe_load(dsl_yaml))

    # Connect client
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    # Run workflow
    result = await client.execute_workflow(
        DSLWorkflow.run,
        dsl_input,
        id=f"dsl-workflow-id-{uuid.uuid4()}",
        task_queue="dsl-task-queue",
    )
    logging.info(
        f"Final variables:\n    "
        + "\n    ".join((f"{k}: {v}" for k, v in result.items()))
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Require the YAML file as an argument. We read this _outside_ of the async
    # def function because thread-blocking IO should never happen in async def
    # functions.
    if len(sys.argv) != 2:
        raise RuntimeError("Expected single argument for YAML file")
    with open(sys.argv[1], "r") as yaml_file:
        dsl_yaml = yaml_file.read()

    # Run
    asyncio.run(main(dsl_yaml))
