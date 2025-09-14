import os
import uuid

import asyncpg
import pytest_asyncio


@pytest_asyncio.fixture
async def db_connection():
    """Create a PostgreSQL connection with a unique schema for each test.

    Sets up a temporary schema with UUID naming, sets it as the default schema
    for the connection, and cleans up with CASCADE on teardown.
    """
    # Generate unique schema name
    schema_name = f"test_{uuid.uuid4().hex}"

    # Create connection
    # Note that we read the DATABASE_URL from the environment because asyncpg does not read this
    # environment variable. It does read other postgres environment variables such as PGHOST,
    # PGPORT, PGDATABASE, PGUSER, and PGPASSWORD, so you can still use those if you do not set
    # DATABASE_URL.
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))

    try:
        # Create the schema
        await conn.execute(f"CREATE SCHEMA {schema_name}")

        # Set the schema as default for this connection
        await conn.execute(f"SET search_path TO {schema_name}")

        yield conn

    finally:
        # Clean up: drop schema with cascade
        try:
            await conn.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
        except Exception:
            pass  # Best effort cleanup
        await conn.close()
