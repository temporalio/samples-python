"""Managed agents CRUD via client.agents.

Managed agents are server-side resources you create, fetch, list, and delete.
Each operation runs as a Temporal activity.
"""

from typing import Any

from temporalio import workflow
from temporalio.contrib.google_genai import TemporalAsyncClient


# @@@SNIPSTART python-google-genai-agents-workflow
@workflow.defn
class AgentsWorkflow:
    @workflow.run
    async def run(self, agent_id: str) -> dict[str, Any]:
        client = TemporalAsyncClient()

        # Creating with a caller-chosen id is not idempotent: if the activity
        # succeeds but its completion is lost, the retry sees "already exists".
        # Real code should generate the id from workflow state and treat that
        # error as success (see this sample's README).
        created = await client.agents.create(
            id=agent_id,
            system_instruction="You are a helpful assistant.",
        )
        try:
            fetched = await client.agents.get(agent_id)
            listing = await client.agents.list(page_size=10)
        finally:
            # Delete in a finally block so a failed get/list doesn't leak the
            # agent on Google's backend.
            await client.agents.delete(agent_id)

        return {
            "created_id": created.id,
            "fetched_id": fetched.id,
            "listed_ids": [a.id for a in (listing.agents or [])],
        }


# @@@SNIPEND
