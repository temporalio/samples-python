import argparse
import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from config import (
    caller_data_converter,
    compressed_encrypted_data_converter,
    encrypted_data_converter,
)
from handler import AsyncEchoHandler, SyncEchoHandler
from service import (
    CALLER_NAMESPACE,
    COMPRESSED_ENCRYPTED_NAMESPACE,
    ENCRYPTED_NAMESPACE,
)
from workflows import CallerWorkflow, EchoWorkflow


async def main(role: str) -> None:
    namespace, data_converter = {
        "caller": (CALLER_NAMESPACE, caller_data_converter),
        "compressed-encrypted": (
            COMPRESSED_ENCRYPTED_NAMESPACE,
            compressed_encrypted_data_converter,
        ),
        "encrypted": (ENCRYPTED_NAMESPACE, encrypted_data_converter),
    }[role]
    client = await Client.connect(
        "localhost:7233", namespace=namespace, data_converter=data_converter()
    )
    async with Worker(
        client,
        task_queue=namespace,
        workflows=[CallerWorkflow] if role == "caller" else [EchoWorkflow],
        nexus_service_handlers=(
            [] if role == "caller" else [SyncEchoHandler(), AsyncEchoHandler()]
        ),
    ):
        print(f"Worker started in {namespace}; press Ctrl+C to stop.", flush=True)
        await asyncio.Event().wait()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("role", choices=["caller", "compressed-encrypted", "encrypted"])
    try:
        asyncio.run(main(parser.parse_args().role))
    except KeyboardInterrupt:
        pass
