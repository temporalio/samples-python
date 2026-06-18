"""Minimal Temporal + Google GenAI workflow: one prompt, one response.

Every Gemini API call made through ``TemporalAsyncClient`` runs as a durable
Temporal activity, so it gets retries, timeouts, and crash recovery for free —
and no credentials ever enter the workflow.
"""

from temporalio import workflow
from temporalio.contrib.google_genai import TemporalAsyncClient


@workflow.defn
class HelloWorldWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        client = TemporalAsyncClient()
        response = await client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text or ""
