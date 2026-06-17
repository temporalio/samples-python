import asyncio
import dataclasses

import aioboto3
import temporalio.converter
from temporalio.client import Client
from temporalio.contrib.aws.s3driver import S3StorageDriver
from temporalio.contrib.aws.s3driver.aioboto3 import new_aioboto3_client
from temporalio.converter import ExternalStorage
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from external_storage.codec import CompressionCodec
from external_storage.workflows import (
    ProcessOrderBatchWorkflow,
    fetch_orders,
    process_orders,
)

S3_ENDPOINT = "http://localhost:5000"
S3_BUCKET = "temporal-payloads"
S3_ACCESS_KEY = "test"
S3_SECRET_KEY = "test"
TASK_QUEUE = "external-storage-task-queue"

interrupt_event = asyncio.Event()


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")

    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name="us-east-1",
    ) as s3_client:
        driver = S3StorageDriver(
            client=new_aioboto3_client(s3_client),
            bucket=S3_BUCKET,
        )

        client = await Client.connect(
            **config,
            data_converter=dataclasses.replace(
                temporalio.converter.default(),
                payload_codec=CompressionCodec(),
                external_storage=ExternalStorage(drivers=[driver]),
            ),
        )

        async with Worker(
            client,
            task_queue=TASK_QUEUE,
            workflows=[ProcessOrderBatchWorkflow],
            activities=[fetch_orders, process_orders],
        ):
            print("Worker started, ctrl+c to exit")
            await interrupt_event.wait()
            print("Shutting down")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
