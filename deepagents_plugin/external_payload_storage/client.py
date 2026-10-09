"""Compose native S3 storage with the Deep Agents data converter."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace

import aioboto3
from temporalio.client import Client
from temporalio.contrib.aws.s3driver import S3StorageDriver
from temporalio.contrib.aws.s3driver.aioboto3 import new_aioboto3_client
from temporalio.deepagents import DeepAgentsPlugin
from temporalio.converter import DataConverter, ExternalStorage
from temporalio.envconfig import ClientConfig

S3_ENDPOINT = "http://localhost:5000"
S3_BUCKET = "temporal-payloads"


@asynccontextmanager
async def connect_client(
    plugin: DeepAgentsPlugin,
    *,
    target_host: str | None = None,
    s3_endpoint: str = S3_ENDPOINT,
) -> AsyncIterator[Client]:
    """Keep the S3 client alive throughout workflow execution and payload reads."""
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    if target_host is not None:
        config["target_host"] = target_host

    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=s3_endpoint,
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1",
    ) as s3_client:
        driver = S3StorageDriver(
            client=new_aioboto3_client(s3_client),
            bucket=S3_BUCKET,
        )
        storage = ExternalStorage(drivers=[driver], payload_size_threshold=256 * 1024)
        plugin.data_converter = replace(
            plugin.data_converter or DataConverter.default,
            external_storage=storage,
        )
        yield await Client.connect(
            **config,
            plugins=[plugin],
        )
