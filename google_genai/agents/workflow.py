"""Managed agents CRUD via client.agents.

Managed agents are server-side resources you create, fetch, list, and delete.
Each operation runs as a Temporal activity.
"""

# @@@SNIPSTART python-google-genai-agents-workflow
from typing import Any

from temporalio import workflow
from temporalio.contrib.google_genai import TemporalAsyncClient


@workflow.defn
class AgentsWorkflow:
    @workflow.run
    async def run(self, agent_id: str) -> dict[str, Any]:
        client = TemporalAsyncClient()

        created = await client.agents.create(
            id=agent_id,
            system_instruction="You are a helpful assistant.",
        )
        fetched = await client.agents.get(agent_id)
        listing = await client.agents.list(page_size=10)
        await client.agents.delete(agent_id)

        return {
            "created_id": created.id,
            "fetched_id": fetched.id,
            "listed_ids": [a.id for a in (listing.agents or [])],
        }


# @@@SNIPEND
