"""Hello world against Vertex AI instead of the Gemini Developer API.

The only difference from the basic sample is configuration: both the workflow's
``TemporalAsyncClient`` and the worker's ``genai.Client`` use ``vertexai=True``
with a Google Cloud project and location. The project and location are passed in
as workflow arguments (read from the environment by the starter) to keep the
workflow deterministic.
"""

# @@@SNIPSTART python-google-genai-vertex-ai-workflow
from temporalio import workflow
from temporalio.contrib.google_genai import TemporalAsyncClient


@workflow.defn
class VertexAIWorkflow:
    @workflow.run
    async def run(self, prompt: str, project: str, location: str) -> str:
        client = TemporalAsyncClient(
            vertexai=True,
            project=project,
            location=location,
        )
        response = await client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text or ""


# @@@SNIPEND
