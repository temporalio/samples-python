from __future__ import annotations

import json
from typing import Any

import asyncpg
from temporalio import activity, workflow
from pydantic import BaseModel
from agents.memory.session import SessionABC
from agents.items import TResponseInputItem
from openai_agents.memory.db_utils import IdempotenceHelper
from typing import Callable

_connection_factory: Callable[[], asyncpg.Connection] | None = None


def _convert_to_json_serializable(obj: Any) -> Any:
    """Recursively convert objects to JSON serializable format."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj

    # Handle Pydantic models
    if hasattr(obj, "model_dump"):
        return _convert_to_json_serializable(obj.model_dump())
    elif hasattr(obj, "dict"):
        return _convert_to_json_serializable(obj.dict())

    # Handle dictionaries
    if isinstance(obj, dict):
        return {key: _convert_to_json_serializable(value) for key, value in obj.items()}

    # Handle lists, tuples, sets
    if isinstance(obj, (list, tuple, set)):
        return [_convert_to_json_serializable(item) for item in obj]

    # Handle other iterables (including ValidatorIterator)
    if hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes)):
        try:
            return [_convert_to_json_serializable(item) for item in obj]
        except Exception:
            # If iteration fails, try to convert to string
            return str(obj)

    # Handle objects with __dict__
    if hasattr(obj, "__dict__"):
        return _convert_to_json_serializable(obj.__dict__)

    # Fallback to string representation
    return str(obj)


class PostgresSessionConfig(BaseModel):
    messages_table: str = "session_messages"
    sessions_table: str = "session"
    operation_id_sequence: str = "session_operation_id_sequence"
    idempotence_table: str = "activity_idempotence"



class PostgresSessionGetItemsRequest(BaseModel):
    config: PostgresSessionConfig
    session_id: str
    limit: int | None = None


class PostgresSessionGetItemsResponse(BaseModel):
    items: list[TResponseInputItem]


@activity.defn
async def postgres_session_get_items_activity(
    request: PostgresSessionGetItemsRequest,
) -> PostgresSessionGetItemsResponse:
    """Get items from the session in operation_id order."""
    activity.heartbeat()

    conn = PostgresSession._get_connection()

    if request.limit is None:
        query = f"""
            SELECT message_data FROM {request.config.messages_table}
            WHERE session_id = $1 AND deleted_at IS NULL
            ORDER BY operation_id ASC
        """
        rows = await conn.fetch(query, request.session_id)
    else:
        query = f"""
            SELECT t.message_data FROM (
                SELECT message_data, operation_id FROM {request.config.messages_table}
                WHERE session_id = $1 AND deleted_at IS NULL
                ORDER BY operation_id DESC
                LIMIT $2
            ) AS t ORDER BY t.operation_id ASC
        """
        rows = await conn.fetch(query, request.session_id, request.limit)

    return PostgresSessionGetItemsResponse(
        items=[json.loads(row["message_data"]) for row in rows]
    )


class PostgresSessionAddItemsRequest(BaseModel):
    config: PostgresSessionConfig
    session_id: str
    items: list[TResponseInputItem]


@activity.defn
async def postgres_session_add_items_activity(
    request: PostgresSessionAddItemsRequest,
) -> None:
    """Add items to the session."""

    conn = PostgresSession._get_connection()

    async def add_items(conn: asyncpg.Connection):
        # Ensure session exists
        await conn.execute(
            f"INSERT INTO {request.config.sessions_table} (session_id) VALUES ($1) ON CONFLICT (session_id) DO NOTHING",
            request.session_id,
        )
        for item in request.items:
            # Use recursive conversion to handle nested objects
            item_dict = _convert_to_json_serializable(item)

            await conn.execute(
                f"INSERT INTO {request.config.messages_table} (session_id, message_data) VALUES ($1, $2)",
                request.session_id,
                json.dumps(item_dict),
            )

    idempotence_helper = IdempotenceHelper(table_name=request.config.idempotence_table)
    await idempotence_helper.idempotent_update(conn, add_items)


class PostgresSessionPopItemRequest(BaseModel):
    config: PostgresSessionConfig
    session_id: str


class PostgresSessionPopItemResponse(BaseModel):
    item: TResponseInputItem | None


@activity.defn
async def postgres_session_pop_item_activity(
    request: PostgresSessionPopItemRequest,
) -> PostgresSessionPopItemResponse:
    """Pop item from the session."""
    conn = PostgresSession._get_connection()

    async def pop_item(conn: asyncpg.Connection):
        row = await conn.fetchrow(
            f"WITH updated AS (UPDATE {request.config.messages_table} SET deleted_at = NOW() WHERE session_id = $1 AND operation_id = (SELECT operation_id FROM {request.config.messages_table} WHERE session_id = $1 AND deleted_at IS NULL ORDER BY operation_id DESC LIMIT 1) RETURNING message_data) SELECT message_data FROM updated",
            request.session_id,
        )
        if row:
            return PostgresSessionPopItemResponse(item=json.loads(row["message_data"]))
        else:
            return PostgresSessionPopItemResponse(item=None)

    idempotence_helper = IdempotenceHelper(table_name=request.config.idempotence_table)
    return await idempotence_helper.idempotent_update(conn, pop_item)


class PostgresSessionClearSessionRequest(BaseModel):
    config: PostgresSessionConfig
    session_id: str


@activity.defn
async def postgres_session_clear_session_activity(
    request: PostgresSessionClearSessionRequest,
) -> None:
    """Clear all items for this session."""
    conn = PostgresSession._get_connection()

    async def clear_session(conn: asyncpg.Connection):
        await conn.execute(
            f"UPDATE {request.config.messages_table} SET deleted_at = NOW() WHERE session_id = $1 AND deleted_at IS NULL",
            request.session_id,
        )

    idempotence_helper = IdempotenceHelper(table_name=request.config.idempotence_table)
    await idempotence_helper.idempotent_update(conn, clear_session)


class PostgresSession(SessionABC):
    """PostgreSQL-based implementation of session storage using operation_id ordering."""

    def __init__(
        self,
        session_id: str,
        config: PostgresSessionConfig,
    ):
        self.session_id = session_id
        self.config = config

    async def get_items(self, limit: int | None = None) -> list[TResponseInputItem]:
        """Retrieve the conversation history for this session."""
        result = await workflow.execute_activity(
            postgres_session_get_items_activity,
            PostgresSessionGetItemsRequest(
                config=self.config, session_id=self.session_id, limit=limit
            ),
            start_to_close_timeout=workflow.timedelta(seconds=30),
        )
        return result.items

    async def add_items(self, items: list[TResponseInputItem]) -> None:
        """Add new items to the conversation history."""
        await workflow.execute_activity(
            postgres_session_add_items_activity,
            PostgresSessionAddItemsRequest(
                config=self.config, session_id=self.session_id, items=items
            ),
            start_to_close_timeout=workflow.timedelta(seconds=30),
        )

    async def pop_item(self) -> TResponseInputItem | None:
        """Remove and return the most recent item from the session."""
        result = await workflow.execute_activity(
            postgres_session_pop_item_activity,
            PostgresSessionPopItemRequest(
                config=self.config, session_id=self.session_id
            ),
            start_to_close_timeout=workflow.timedelta(seconds=30),
        )
        return result.item

    async def clear_session(self) -> None:
        """Clear all items for this session."""
        await workflow.execute_activity(
            postgres_session_clear_session_activity,
            PostgresSessionClearSessionRequest(
                config=self.config, session_id=self.session_id
            ),
            start_to_close_timeout=workflow.timedelta(seconds=30),
        )

    @staticmethod
    def set_connection_factory(factory: Callable[[], asyncpg.Connection]):
        global _connection_factory
        _connection_factory = factory

    @staticmethod
    def _get_connection():
        if _connection_factory is None:
            raise ValueError("Connection factory not set")
        return _connection_factory()

    @staticmethod
    async def init_schema(config: PostgresSessionConfig) -> None:
        conn = PostgresSession._get_connection()
        """Initialize the PostgreSQL schema."""
        async with conn.transaction():
            # Create sessions table
            sessions_ddl = f"""
                CREATE TABLE IF NOT EXISTS {config.sessions_table} (
                    session_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    PRIMARY KEY (session_id)
                )
            """
            await conn.execute(sessions_ddl)

            # Create operation_id sequence
            operation_id_ddl = f"""
                CREATE SEQUENCE IF NOT EXISTS {config.operation_id_sequence} START 1
            """
            await conn.execute(operation_id_ddl)

            # Create messages table
            messages_ddl = f"""
                CREATE TABLE IF NOT EXISTS {config.messages_table} (
                    session_id TEXT NOT NULL,
                    operation_id INTEGER NOT NULL DEFAULT nextval('{config.operation_id_sequence}'),
                    message_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    deleted_at TIMESTAMP NULL,
                    PRIMARY KEY (session_id, operation_id),
                    FOREIGN KEY (session_id) 
                    REFERENCES {config.sessions_table} (session_id)
                    ON DELETE CASCADE
                )
            """
            await conn.execute(messages_ddl)

    @staticmethod
    def get_activities() -> list[Callable[[], activity.Activity]]:
        return [
            postgres_session_get_items_activity,
            postgres_session_add_items_activity,
            postgres_session_pop_item_activity,
            postgres_session_clear_session_activity,
        ]