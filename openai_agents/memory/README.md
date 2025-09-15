# Session Memory Examples

Session memory examples for OpenAI Agents SDK integrated with Temporal workflows.

*Adapted from [OpenAI Agents SDK session memory examples](https://github.com/openai/openai-agents-python/tree/main/examples/memory)*

Before running these examples, be sure to review the [prerequisites and background on the integration](../README.md).

## Running the Examples

### PostgreSQL Session Memory

This example uses a PostgreSQL database to store session data.

You need can use the standard PostgreSQL environment variables to configure the database connection.
These include `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGHOST`, and `PGPORT`.
We also support the `DATABASE_URL` environment variable.

To confirm that your environment is configured correctly, just run the `psql` command after setting the environment variables.
For example:
```bash
PGDATABASE=postgres psql
```

Start the worker:
```bash
PGDATABASE=postgres uv run openai_agents/memory/run_postgres_session_worker.py
```

Then run the workflow:

```bash
uv run openai_agents/memory/run_postgres_session_workflow.py
```
