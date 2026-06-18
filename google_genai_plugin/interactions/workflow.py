"""Stateful server-side conversations via the Interactions API.

``client.interactions`` is a server-managed API: the conversation state lives on
Google's backend, addressed by an interaction id. Each operation — create, get,
delete — runs as a Temporal activity. Unlike ``client.models``, this API has no
automatic function calling.
"""

from typing import Any

from temporalio import workflow
from temporalio.contrib.google_genai import TemporalAsyncClient


@workflow.defn
class InteractionsWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> dict[str, Any]:
        client = TemporalAsyncClient()

        interaction = await client.interactions.create(
            model="gemini-2.5-flash",
            input=prompt,
        )
        fetched = await client.interactions.get(interaction.id)
        await client.interactions.delete(interaction.id)

        return {"id": interaction.id, "status": str(fetched.status)}
