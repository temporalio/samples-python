import asyncio
import traceback
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

import rich
from temporalio import workflow
from temporalio.client import Client
from temporalio.contrib.opentelemetry import TracingInterceptor

from dan.constants import NAMESPACE


async def connect(tracing_interceptor: bool = False) -> Client:
    return await Client.connect(
        "localhost:7233",
        namespace=NAMESPACE,
        interceptors=[TracingInterceptor()] if tracing_interceptor else [],
    )


def print(*args, **kwargs):
    with workflow.unsafe.imports_passed_through():
        rich.print(*args, **kwargs)


@contextmanager
def catch():
    try:
        yield
    except Exception as err:
        import pdb

        pdb.set_trace()
        print(err)


async def ainput(prompt: str = ""):
    with ThreadPoolExecutor(1, "ainput") as executor:
        return (
            await asyncio.get_event_loop().run_in_executor(executor, input, prompt)
        ).rstrip()


def print_stack():
    stack = traceback.extract_stack()
    formatted_stack = traceback.format_list(stack)
    for line in formatted_stack:
        print(line.strip())
