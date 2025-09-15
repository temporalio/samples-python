import json
import asyncpg
from typing import Callable, Awaitable, TypeVar
from temporalio import activity
from pydantic import BaseModel

T = TypeVar("T")


class IdempotenceHelper(BaseModel):
    table_name: str

    def __init__(self, table_name: str):
        super().__init__(table_name=table_name)
        self.table_name = table_name

    async def create_table(self, conn: asyncpg.Connection) -> None:
        await conn.execute(
            f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    run_id UUID NOT NULL,
                    activity_id TEXT NOT NULL,
                    operation_started_at TIMESTAMP NOT NULL,
                    operation_completed_at TIMESTAMP NULL,
                    operation_result TEXT NULL,
                    PRIMARY KEY (run_id, activity_id)
                )
            """
        )

    async def idempotent_update(
        self,
        conn: asyncpg.Connection,
        operation: Callable[[asyncpg.Connection], Awaitable[T]],
    ) -> T | None:
        """Insert idempotence row; on conflict, read and return existing result.

        The operation must be an async callable of the form:
            async def op(conn: asyncpg.Connection) -> T
        """
        activity_info = activity.info()
        run_id = activity_info.workflow_run_id
        activity_id = activity_info.activity_id

        async with conn.transaction():
            did_insert = await conn.fetchrow(
                (
                    f"INSERT INTO {self.table_name} "
                    f"(run_id, activity_id, operation_started_at) "
                    f"VALUES ($1, $2, NOW()) "
                    f"ON CONFLICT (run_id, activity_id) DO NOTHING "
                    f"RETURNING 1"
                ),
                run_id,
                activity_id,
            )

            if did_insert:
                res = await operation(conn)

                if hasattr(res, "model_dump_json"):
                    op_result = res.model_dump_json()
                else:
                    op_result = json.dumps(res)

                await conn.execute(
                    f"UPDATE {self.table_name} SET operation_completed_at = NOW(), operation_result = $1 WHERE run_id = $2 AND activity_id = $3",
                    op_result,
                    run_id,
                    activity_id,
                )
                return res
            else:
                row = await conn.fetchrow(
                    f"SELECT operation_result FROM {self.table_name} WHERE run_id = $1 AND activity_id = $2",
                    run_id,
                    activity_id,
                )
                if not row or row["operation_result"] is None:
                    return None
                try:
                    return json.loads(row["operation_result"])
                except Exception:
                    return row["operation_result"]
