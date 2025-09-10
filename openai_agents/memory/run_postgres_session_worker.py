from __future__ import annotations

import asyncio
import os
import asyncpg
from datetime import timedelta

from temporalio.client import Client
from temporalio.contrib.openai_agents import ModelActivityParameters, OpenAIAgentsPlugin
from temporalio.worker import Worker

from openai_agents.memory.workflows.postgres_session_workflow import (
    PostgresSessionWorkflow,
)
from openai_agents.memory.postgres_session import (
    PostgresSessionConfig,
    init_schema,
    PostgresSession,
    postgres_session_get_items_activity,
    postgres_session_add_items_activity,
    postgres_session_pop_item_activity,
    postgres_session_clear_session_activity,
)
from openai_agents.memory.db_utils import IdempotenceHelper


async def main():
    db_connection = await asyncpg.connect(os.getenv("DATABASE_URL"))

    # Database setup
    postgres_session_config = PostgresSessionConfig(
        messages_table="session_messages",
        sessions_table="session",
        operation_id_sequence="session_operation_id_sequence",
    )
    PostgresSession.set_connection_factory(lambda: db_connection)
    await init_schema(db_connection, config=postgres_session_config)
    idempotence_helper = IdempotenceHelper(table_name="activity_idempotence")
    await idempotence_helper.create_table(db_connection)
    PostgresSession.set_connection_factory(lambda: db_connection)

    # Create client connected to server at the given address
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(
                model_params=ModelActivityParameters(
                    start_to_close_timeout=timedelta(seconds=30)
                )
            ),
        ],
    )

    worker = Worker(
        client,
        task_queue="openai-agents-memory-task-queue",
        workflows=[
            PostgresSessionWorkflow,
        ],
        activities=[
            postgres_session_get_items_activity,
            postgres_session_add_items_activity,
            postgres_session_pop_item_activity,
            postgres_session_clear_session_activity,
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
