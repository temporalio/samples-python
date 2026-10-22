"""Configure native S3 External Storage for the Deep Agents plugin."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import aioboto3
from langchain_core.messages import AIMessage
from temporalio.client import Client
from temporalio.contrib.aws.s3driver import S3StorageDriver
from temporalio.contrib.aws.s3driver.aioboto3 import new_aioboto3_client
from temporalio.converter import DataConverter, ExternalStorage
from temporalio.deepagents import DeepAgentsPlugin
from temporalio.deepagents.testing import mock_model_provider
from temporalio.envconfig import ClientConfig

S3_ENDPOINT = "http://localhost:5000"
S3_BUCKET = "temporal-payloads"


@asynccontextmanager
async def connect_client(
    *,
    target_host: str | None = None,
    s3_endpoint: str = S3_ENDPOINT,
) -> AsyncIterator[Client]:
    """Keep the S3 client alive while Temporal reads and writes payloads."""
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
        storage = ExternalStorage(drivers=[driver])
        data_converter = DataConverter(external_storage=storage)
        # Script the model so the demo needs no LLM provider or API key.
        plugin = DeepAgentsPlugin(
            data_converter=data_converter,
            model_provider=mock_model_provider(
                [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "read_file",
                                "args": {"file_path": "large-document.txt"},
                                "id": "call-read",
                            }
                        ],
                    ),
                    AIMessage(content="I received the complete document."),
                ]
            ),
        )
        yield await Client.connect(**config, plugins=[plugin])
