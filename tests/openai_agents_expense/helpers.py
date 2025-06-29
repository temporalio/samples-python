"""
Helper functions for OpenAI Agents Expense Processing tests.
"""

import uuid
from contextlib import asynccontextmanager
from typing import Any, List, Optional, Type

from temporalio.client import Client
from temporalio.worker import Worker


@asynccontextmanager
async def new_worker(
    client: Client,
    *workflows: Type[Any],
    activities: Optional[List[Any]] = None,
    task_queue: Optional[str] = None,
    **kwargs,
):
    """
    Create a new test worker with the given workflows and activities.

    Args:
        client: The Temporal client
        *workflows: Workflow classes to register
        activities: Optional list of activity functions
        task_queue: Optional task queue name (generates random if not provided)
        **kwargs: Additional arguments for Worker

    Yields:
        Configured Worker instance
    """
    if task_queue is None:
        task_queue = f"test-{uuid.uuid4()}"

    if activities is None:
        activities = []

    # Create worker with pydantic data converter (client already has it)
    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=list(workflows),
        activities=activities,
        **kwargs,
    )

    try:
        # Start the worker
        async with worker:
            yield worker
    finally:
        # Worker cleanup happens automatically with async context manager
        pass
