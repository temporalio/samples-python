import asyncio
import dataclasses
from datetime import datetime

import aioboto3
import temporalio.converter
from temporalio.client import Client
from temporalio.contrib.aws.s3driver import S3StorageDriver
from temporalio.contrib.aws.s3driver.aioboto3 import new_aioboto3_client
from temporalio.converter import ExternalStorage
from temporalio.envconfig import ClientConfig

from external_storage.codec import CompressionCodec
from external_storage.worker import (
    S3_ACCESS_KEY,
    S3_BUCKET,
    S3_ENDPOINT,
    S3_SECRET_KEY,
    TASK_QUEUE,
)
from external_storage.workflows import OrderBatchRequest, ProcessOrderBatchWorkflow

ORDER_COUNT = 200


async def main() -> None:
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

        config = ClientConfig.load_client_connect_config()
        config.setdefault("target_host", "localhost:7233")

        client = await Client.connect(
            **config,
            data_converter=dataclasses.replace(
                temporalio.converter.default(),
                payload_codec=CompressionCodec(),
                external_storage=ExternalStorage(drivers=[driver]),
            ),
        )

        run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        workflow_id = f"external-storage-{run_id}"
        request = OrderBatchRequest(batch_id=f"BATCH-{run_id}", order_count=ORDER_COUNT)

        print(
            f"Starting workflow {workflow_id} (batch_id={request.batch_id}, "
            f"order_count={request.order_count})"
        )

        summary = await client.execute_workflow(
            ProcessOrderBatchWorkflow.run,
            request,
            id=workflow_id,
            task_queue=TASK_QUEUE,
        )

    print(f"\nBatch {summary.batch_id}: {summary.order_count} orders processed")
    print(f"  Total shipping cost: ${summary.total_shipping_cost_usd:,.2f}")
    print(f"  Total weight:        {summary.total_weight_kg:,.1f} kg")
    print(f"  Avg delivery:        {summary.avg_delivery_days} days")


if __name__ == "__main__":
    asyncio.run(main())
