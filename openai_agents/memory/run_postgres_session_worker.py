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
    PostgresSession,
)
from openai_agents.memory.db_utils import IdempotenceHelper


async def main():
    db_connection = await asyncpg.connect(os.getenv("DATABASE_URL"))

    # Database setup
    postgres_session_config = PostgresSessionConfig(
        messages_table="session_messages",
        sessions_table="session",
        operation_id_sequence="session_operation_id_sequence",
        idempotence_table="activity_idempotence",
    )

    # Create the idempotence table. This is used to ensure that activities are idempotent with
    # respect to database modifications.
    idempotence_helper = IdempotenceHelper(table_name=postgres_session_config.idempotence_table)
    await idempotence_helper.create_table(db_connection)

    # Configure the Postgres Session with the database connection.
    # Initialize the schema.
    PostgresSession.set_connection_factory(lambda: db_connection)
    await PostgresSession.init_schema(config=postgres_session_config)

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
        task_queue="openai-postgres-session-task-queue",
        workflows=[
            PostgresSessionWorkflow,
        ],
        activities=[*PostgresSession.get_activities()],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
