import uuid
from datetime import datetime
from ipaddress import IPv4Address

from temporalio.client import Client
from temporalio.worker import Worker

from pydantic_converter_v1.converter import pydantic_data_converter
from pydantic_converter_v1.worker import (
    MyPydanticModel,
    MyWorkflow,
    my_activity,
    new_sandbox_runner,
)


async def test_workflow_with_pydantic_model(client: Client):
    # Replace data converter in client
    new_config = client.config()
    new_config["data_converter"] = pydantic_data_converter
    client = Client(**new_config)
    task_queue_name = str(uuid.uuid4())

    orig_models = [
        MyPydanticModel(
            some_ip=IPv4Address("127.0.0.1"), some_date=datetime(2000, 1, 2, 3, 4, 5)
        ),
        MyPydanticModel(
            some_ip=IPv4Address("127.0.0.2"), some_date=datetime(2001, 2, 3, 4, 5, 6)
        ),
    ]

    async with Worker(
        client,
        task_queue=task_queue_name,
        workflows=[MyWorkflow],
        activities=[my_activity],
        workflow_runner=new_sandbox_runner(),
    ):
        result = await client.execute_workflow(
            MyWorkflow.run,
            orig_models,
            id=str(uuid.uuid4()),
            task_queue=task_queue_name,
        )
    assert orig_models == result
