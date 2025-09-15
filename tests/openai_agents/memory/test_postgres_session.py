import asyncpg
from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import Worker

import uuid
from datetime import timedelta

from openai_agents.memory.db_utils import IdempotenceHelper
from openai_agents.memory.postgres_session import PostgresSessionConfig
from openai_agents.memory.postgres_session import PostgresSession
from openai_agents.memory.postgres_session import TResponseInputItem
from openai_agents.memory.postgres_session import (
    init_schema,
    postgres_session_pop_item_activity,
    postgres_session_add_items_activity,
    postgres_session_clear_session_activity,
    postgres_session_get_items_activity,
)
from pydantic import BaseModel
from temporalio.contrib.pydantic import pydantic_data_converter


class BasicSessionWorkflowConfig(BaseModel):
    session_id: str
    config: PostgresSessionConfig


@workflow.defn
class BasicSessionWorkflow:
    @workflow.run
    async def run(self, config: BasicSessionWorkflowConfig):
        session = PostgresSession(session_id=config.session_id, config=config.config)
        # Test adding and retrieving items
        items: list[TResponseInputItem] = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        await session.add_items(items)
        retrieved = await session.get_items()

        assert len(retrieved) == 2
        assert retrieved[0].get("role") == "user"
        assert retrieved[0].get("content") == "Hello"
        assert retrieved[1].get("role") == "assistant"
        assert retrieved[1].get("content") == "Hi there!"

        # Test clearing session
        await session.clear_session()
        retrieved_after_clear = await session.get_items()
        assert len(retrieved_after_clear) == 0


async def test_session_workflow(client: Client, db_connection: asyncpg.Connection):
    new_config = client.config()
    new_config["data_converter"] = pydantic_data_converter
    client = Client(**new_config)

    postgres_session_config = PostgresSessionConfig(
        messages_table="session_messages",
        sessions_table="session",
        operation_id_sequence="session_operation_id_sequence",
    )
    PostgresSession.set_connection_factory(lambda: db_connection)
    await init_schema(db_connection, config=postgres_session_config)

    idempotence_helper = IdempotenceHelper(table_name="activity_idempotence")
    await idempotence_helper.create_table(db_connection)

    async with Worker(
        client,
        task_queue=f"basic-session-workflow-{uuid.uuid4()}",
        workflows=[BasicSessionWorkflow],
        activities=[
            postgres_session_pop_item_activity,
            postgres_session_add_items_activity,
            postgres_session_clear_session_activity,
            postgres_session_get_items_activity,
        ],
    ) as worker:
        workflow_handle = await client.start_workflow(
            BasicSessionWorkflow.run,
            BasicSessionWorkflowConfig(
                session_id=f"test-session-{uuid.uuid4()}",
                config=postgres_session_config,
            ),
            id=f"basic-session-workflow-{uuid.uuid4()}",
            task_queue=worker.task_queue,
            execution_timeout=timedelta(seconds=10),
        )
        await workflow_handle.result()


# Pop item workflow and tests
@workflow.defn
class PopItemWorkflow:
    @workflow.run
    async def run(self, config: BasicSessionWorkflowConfig):
        session = PostgresSession(session_id=config.session_id, config=config.config)

        # Test popping from empty session
        popped = await session.pop_item()
        assert popped is None

        # Add items
        items: list[TResponseInputItem] = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]
        await session.add_items(items)

        # Verify all items are there
        retrieved = await session.get_items()
        assert len(retrieved) == 3

        # Pop the most recent item
        popped = await session.pop_item()
        assert popped is not None
        assert popped.get("role") == "user"
        assert popped.get("content") == "How are you?"

        # Verify item was removed
        retrieved_after_pop = await session.get_items()
        assert len(retrieved_after_pop) == 2
        assert retrieved_after_pop[-1].get("content") == "Hi there!"

        # Pop another item
        popped2 = await session.pop_item()
        assert popped2 is not None
        assert popped2.get("role") == "assistant"
        assert popped2.get("content") == "Hi there!"

        # Pop the last item
        popped3 = await session.pop_item()
        assert popped3 is not None
        assert popped3.get("role") == "user"
        assert popped3.get("content") == "Hello"

        # Try to pop from empty session again
        popped4 = await session.pop_item()
        assert popped4 is None

        # Verify session is empty
        final_items = await session.get_items()
        assert len(final_items) == 0


async def test_postgres_session_pop_item(
    client: Client, db_connection: asyncpg.Connection
):
    """Test PostgresSession pop_item functionality."""
    new_config = client.config()
    new_config["data_converter"] = pydantic_data_converter
    client = Client(**new_config)

    postgres_session_config = PostgresSessionConfig(
        messages_table="session_messages",
        sessions_table="session",
        operation_id_sequence="session_operation_id_sequence",
    )
    PostgresSession.set_connection_factory(lambda: db_connection)
    await init_schema(db_connection, config=postgres_session_config)

    idempotence_helper = IdempotenceHelper(table_name="activity_idempotence")
    await idempotence_helper.create_table(db_connection)

    async with Worker(
        client,
        task_queue=f"pop-item-workflow-{uuid.uuid4()}",
        workflows=[PopItemWorkflow],
        activities=[
            postgres_session_pop_item_activity,
            postgres_session_add_items_activity,
            postgres_session_clear_session_activity,
            postgres_session_get_items_activity,
        ],
    ) as worker:
        workflow_handle = await client.start_workflow(
            PopItemWorkflow.run,
            BasicSessionWorkflowConfig(
                session_id=f"pop-test-{uuid.uuid4()}", config=postgres_session_config
            ),
            id=f"pop-item-workflow-{uuid.uuid4()}",
            task_queue=worker.task_queue,
            execution_timeout=timedelta(seconds=10),
        )
        await workflow_handle.result()


# Test different sessions workflow
@workflow.defn
class DifferentSessionsWorkflow:
    @workflow.run
    async def run(self, config: BasicSessionWorkflowConfig):
        # Create two sessions with different IDs
        session_1_id = f"session_1_{config.session_id}"
        session_2_id = f"session_2_{config.session_id}"

        session_1 = PostgresSession(session_id=session_1_id, config=config.config)
        session_2 = PostgresSession(session_id=session_2_id, config=config.config)

        # Add items to both sessions
        items_1: list[TResponseInputItem] = [
            {"role": "user", "content": "Session 1 message"},
        ]
        items_2: list[TResponseInputItem] = [
            {"role": "user", "content": "Session 2 message 1"},
            {"role": "user", "content": "Session 2 message 2"},
        ]

        await session_1.add_items(items_1)
        await session_2.add_items(items_2)

        # Pop from session 2
        popped = await session_2.pop_item()
        assert popped is not None
        assert popped.get("content") == "Session 2 message 2"

        # Verify session 1 is unaffected
        session_1_items = await session_1.get_items()
        assert len(session_1_items) == 1
        assert session_1_items[0].get("content") == "Session 1 message"

        # Verify session 2 has one item left
        session_2_items = await session_2.get_items()
        assert len(session_2_items) == 1
        assert session_2_items[0].get("content") == "Session 2 message 1"


async def test_postgres_session_pop_different_sessions(
    client: Client, db_connection: asyncpg.Connection
):
    """Test that pop_item only affects the specified session."""
    new_config = client.config()
    new_config["data_converter"] = pydantic_data_converter
    client = Client(**new_config)

    postgres_session_config = PostgresSessionConfig(
        messages_table="session_messages",
        sessions_table="session",
        operation_id_sequence="session_operation_id_sequence",
    )
    PostgresSession.set_connection_factory(lambda: db_connection)
    await init_schema(db_connection, config=postgres_session_config)

    idempotence_helper = IdempotenceHelper(table_name="activity_idempotence")
    await idempotence_helper.create_table(db_connection)

    async with Worker(
        client,
        task_queue=f"different-sessions-workflow-{uuid.uuid4()}",
        workflows=[DifferentSessionsWorkflow],
        activities=[
            postgres_session_pop_item_activity,
            postgres_session_add_items_activity,
            postgres_session_clear_session_activity,
            postgres_session_get_items_activity,
        ],
    ) as worker:
        workflow_handle = await client.start_workflow(
            DifferentSessionsWorkflow.run,
            BasicSessionWorkflowConfig(
                session_id=f"diff-sessions-test-{uuid.uuid4()}",
                config=postgres_session_config,
            ),
            id=f"different-sessions-workflow-{uuid.uuid4()}",
            task_queue=worker.task_queue,
            execution_timeout=timedelta(seconds=10),
        )
        await workflow_handle.result()


# Test get_items with limit workflow
@workflow.defn
class GetItemsWithLimitWorkflow:
    @workflow.run
    async def run(self, config: BasicSessionWorkflowConfig):
        session = PostgresSession(session_id=config.session_id, config=config.config)

        # Add multiple items
        items: list[TResponseInputItem] = [
            {"role": "user", "content": "Message 1"},
            {"role": "assistant", "content": "Response 1"},
            {"role": "user", "content": "Message 2"},
            {"role": "assistant", "content": "Response 2"},
            {"role": "user", "content": "Message 3"},
            {"role": "assistant", "content": "Response 3"},
        ]
        await session.add_items(items)

        # Test getting all items (default behavior)
        all_items = await session.get_items()
        assert len(all_items) == 6
        assert all_items[0].get("content") == "Message 1"
        assert all_items[-1].get("content") == "Response 3"

        # Test getting latest 2 items
        latest_2 = await session.get_items(limit=2)
        assert len(latest_2) == 2
        assert latest_2[0].get("content") == "Message 3"
        assert latest_2[1].get("content") == "Response 3"

        # Test getting latest 4 items
        latest_4 = await session.get_items(limit=4)
        assert len(latest_4) == 4
        assert latest_4[0].get("content") == "Message 2"
        assert latest_4[1].get("content") == "Response 2"
        assert latest_4[2].get("content") == "Message 3"
        assert latest_4[3].get("content") == "Response 3"

        # Test getting more items than available
        latest_10 = await session.get_items(limit=10)
        assert len(latest_10) == 6  # Should return all available items
        assert latest_10[0].get("content") == "Message 1"
        assert latest_10[-1].get("content") == "Response 3"

        # Test getting 0 items
        latest_0 = await session.get_items(limit=0)
        assert len(latest_0) == 0


async def test_postgres_session_get_items_with_limit(
    client: Client, db_connection: asyncpg.Connection
):
    """Test PostgresSession get_items with limit parameter."""
    new_config = client.config()
    new_config["data_converter"] = pydantic_data_converter
    client = Client(**new_config)

    postgres_session_config = PostgresSessionConfig(
        messages_table="session_messages",
        sessions_table="session",
        operation_id_sequence="session_operation_id_sequence",
    )
    PostgresSession.set_connection_factory(lambda: db_connection)
    await init_schema(db_connection, config=postgres_session_config)

    idempotence_helper = IdempotenceHelper(table_name="activity_idempotence")
    await idempotence_helper.create_table(db_connection)

    async with Worker(
        client,
        task_queue=f"get-items-limit-workflow-{uuid.uuid4()}",
        workflows=[GetItemsWithLimitWorkflow],
        activities=[
            postgres_session_pop_item_activity,
            postgres_session_add_items_activity,
            postgres_session_clear_session_activity,
            postgres_session_get_items_activity,
        ],
    ) as worker:
        workflow_handle = await client.start_workflow(
            GetItemsWithLimitWorkflow.run,
            BasicSessionWorkflowConfig(
                session_id=f"limit-test-{uuid.uuid4()}", config=postgres_session_config
            ),
            id=f"get-items-limit-workflow-{uuid.uuid4()}",
            task_queue=worker.task_queue,
            execution_timeout=timedelta(seconds=10),
        )
        await workflow_handle.result()


# Test unicode content workflow
@workflow.defn
class UnicodeContentWorkflow:
    @workflow.run
    async def run(self, config: BasicSessionWorkflowConfig):
        session = PostgresSession(session_id=config.session_id, config=config.config)

        # Add unicode content to the session
        items: list[TResponseInputItem] = [
            {"role": "user", "content": "こんにちは"},
            {"role": "assistant", "content": "😊👍"},
            {"role": "user", "content": "Привет"},
        ]
        await session.add_items(items)

        # Retrieve items and verify unicode content
        retrieved = await session.get_items()
        assert retrieved[0].get("content") == "こんにちは"
        assert retrieved[1].get("content") == "😊👍"
        assert retrieved[2].get("content") == "Привет"


async def test_postgres_session_unicode_content(
    client: Client, db_connection: asyncpg.Connection
):
    """Test that session correctly stores and retrieves unicode/non-ASCII content."""
    new_config = client.config()
    new_config["data_converter"] = pydantic_data_converter
    client = Client(**new_config)

    postgres_session_config = PostgresSessionConfig(
        messages_table="session_messages",
        sessions_table="session",
        operation_id_sequence="session_operation_id_sequence",
    )
    PostgresSession.set_connection_factory(lambda: db_connection)
    await init_schema(db_connection, config=postgres_session_config)

    idempotence_helper = IdempotenceHelper(table_name="activity_idempotence")
    await idempotence_helper.create_table(db_connection)

    async with Worker(
        client,
        task_queue=f"unicode-content-workflow-{uuid.uuid4()}",
        workflows=[UnicodeContentWorkflow],
        activities=[
            postgres_session_pop_item_activity,
            postgres_session_add_items_activity,
            postgres_session_clear_session_activity,
            postgres_session_get_items_activity,
        ],
    ) as worker:
        workflow_handle = await client.start_workflow(
            UnicodeContentWorkflow.run,
            BasicSessionWorkflowConfig(
                session_id=f"unicode-test-{uuid.uuid4()}",
                config=postgres_session_config,
            ),
            id=f"unicode-content-workflow-{uuid.uuid4()}",
            task_queue=worker.task_queue,
            execution_timeout=timedelta(seconds=10),
        )
        await workflow_handle.result()


# Test special characters and SQL injection workflow
@workflow.defn
class SpecialCharactersWorkflow:
    @workflow.run
    async def run(self, config: BasicSessionWorkflowConfig):
        session = PostgresSession(session_id=config.session_id, config=config.config)

        # Add items with special characters and SQL keywords
        items: list[TResponseInputItem] = [
            {"role": "user", "content": "O'Reilly"},
            {"role": "assistant", "content": "DROP TABLE sessions;"},
            {
                "role": "user",
                "content": '"SELECT * FROM users WHERE name = \\"admin\\";";',
            },
            {"role": "assistant", "content": "Robert'); DROP TABLE students;--"},
            {"role": "user", "content": "Normal message"},
        ]
        await session.add_items(items)

        # Retrieve all items and verify they are stored correctly
        retrieved = await session.get_items()
        assert len(retrieved) == len(items)
        assert retrieved[0].get("content") == "O'Reilly"
        assert retrieved[1].get("content") == "DROP TABLE sessions;"
        assert (
            retrieved[2].get("content")
            == '"SELECT * FROM users WHERE name = \\"admin\\";";'
        )
        assert retrieved[3].get("content") == "Robert'); DROP TABLE students;--"
        assert retrieved[4].get("content") == "Normal message"


async def test_postgres_session_special_characters_and_sql_injection(
    client: Client, db_connection: asyncpg.Connection
):
    """Test that session safely stores and retrieves items with special characters and SQL keywords."""
    new_config = client.config()
    new_config["data_converter"] = pydantic_data_converter
    client = Client(**new_config)

    postgres_session_config = PostgresSessionConfig(
        messages_table="session_messages",
        sessions_table="session",
        operation_id_sequence="session_operation_id_sequence",
    )
    PostgresSession.set_connection_factory(lambda: db_connection)
    await init_schema(db_connection, config=postgres_session_config)

    idempotence_helper = IdempotenceHelper(table_name="activity_idempotence")
    await idempotence_helper.create_table(db_connection)

    async with Worker(
        client,
        task_queue=f"special-chars-workflow-{uuid.uuid4()}",
        workflows=[SpecialCharactersWorkflow],
        activities=[
            postgres_session_pop_item_activity,
            postgres_session_add_items_activity,
            postgres_session_clear_session_activity,
            postgres_session_get_items_activity,
        ],
    ) as worker:
        workflow_handle = await client.start_workflow(
            SpecialCharactersWorkflow.run,
            BasicSessionWorkflowConfig(
                session_id=f"special-chars-test-{uuid.uuid4()}",
                config=postgres_session_config,
            ),
            id=f"special-chars-workflow-{uuid.uuid4()}",
            task_queue=worker.task_queue,
            execution_timeout=timedelta(seconds=10),
        )
        await workflow_handle.result()
