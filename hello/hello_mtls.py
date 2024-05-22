import argparse
import asyncio
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.service import TLSConfig
from temporalio.worker import Worker


@dataclass
class ComposeGreetingInput:
    greeting: str
    name: str


# Basic activity that logs and does string concatenation
@activity.defn
async def compose_greeting(input: ComposeGreetingInput) -> str:
    return f"{input.greeting}, {input.name}!"


# Basic workflow that logs and invokes an activity
@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        return await workflow.execute_activity(
            compose_greeting,
            ComposeGreetingInput("Hello", name),
            start_to_close_timeout=timedelta(seconds=10),
        )


async def main():
    # Load certs from CLI args
    parser = argparse.ArgumentParser(description="Use mTLS with server")
    parser.add_argument(
        "--target-host", help="Host:port for the server", default="localhost:7233"
    )
    parser.add_argument(
        "--namespace", help="Namespace for the server", default="default"
    )
    parser.add_argument(
        "--server-root-ca-cert", help="Optional path to root server CA cert"
    )
    parser.add_argument(
        "--client-cert", help="Required path to client cert", required=True
    )
    parser.add_argument(
        "--client-key", help="Required path to client key", required=True
    )
    args = parser.parse_args()
    server_root_ca_cert: Optional[bytes] = None
    if args.server_root_ca_cert:
        with open(args.server_root_ca_cert, "rb") as f:
            server_root_ca_cert = f.read()
    with open(args.client_cert, "rb") as f:
        client_cert = f.read()
    with open(args.client_key, "rb") as f:
        client_key = f.read()

    # Start client with TLS configured
    client = await Client.connect(
        args.target_host,
        namespace=args.namespace,
        tls=TLSConfig(
            server_root_ca_cert=server_root_ca_cert,
            client_cert=client_cert,
            client_private_key=client_key,
        ),
    )

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="hello-mtls-task-queue",
        workflows=[GreetingWorkflow],
        activities=[compose_greeting],
    ):

        # While the worker is running, use the client to run the workflow and
        # print out its result. Note, in many production setups, the client
        # would be in a completely separate process from the worker.
        result = await client.execute_workflow(
            GreetingWorkflow.run,
            "World",
            id="hello-mtls-workflow-id",
            task_queue="hello-mtls-task-queue",
        )
        print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
