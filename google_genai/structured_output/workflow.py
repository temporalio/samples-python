"""Typed JSON output via response_schema + a Pydantic model.

The plugin installs a ``PydanticPayloadConverter``, so a Pydantic model flows
through Temporal payloads cleanly. Passing the model as ``response_schema``
makes Gemini return matching JSON, which the SDK parses into the model on
``response.parsed``.
"""

from google.genai import types
from pydantic import BaseModel
from temporalio import workflow
from temporalio.contrib.google_genai import TemporalAsyncClient
from temporalio.exceptions import ApplicationError


# @@@SNIPSTART python-google-genai-structured-output-workflow
class Recipe(BaseModel):
    name: str
    ingredients: list[str]
    steps: list[str]


@workflow.defn
class StructuredOutputWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> Recipe:
        client = TemporalAsyncClient()
        response = await client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=Recipe,
            ),
        )
        recipe = response.parsed
        if not isinstance(recipe, Recipe):
            # ``parsed`` is None when the model returns malformed JSON. Fail the
            # workflow with an ApplicationError rather than asserting: an
            # assertion is a workflow task failure, which Temporal retries
            # forever, so the run would hang instead of failing visibly.
            raise ApplicationError(
                f"Gemini did not return a valid Recipe: {response.text!r}",
                non_retryable=True,
            )
        return recipe


# @@@SNIPEND
