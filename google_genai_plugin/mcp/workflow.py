"""Use an MCP server's tools from a Gemini call via TemporalMcpClientSession.

The worker registers an ``echo`` MCP server with the plugin. Inside the
workflow, ``TemporalMcpClientSession("echo")`` is passed as a tool; Gemini's AFC
loop discovers and calls the MCP tools, with ``list_tools`` / ``call_tool``
running as Temporal activities against a pooled worker-side connection.
"""

# @@@SNIPSTART python-google-genai-mcp-workflow
from datetime import timedelta

from google.genai import types
from temporalio import workflow
from temporalio.contrib.google_genai import (
    TemporalAsyncClient,
    TemporalMcpClientSession,
)
from temporalio.workflow import ActivityConfig


@workflow.defn
class McpWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        client = TemporalAsyncClient()
        session = TemporalMcpClientSession(
            "echo",
            cache_tools=True,
            activity_config=ActivityConfig(
                start_to_close_timeout=timedelta(seconds=30),
            ),
        )
        response = await client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(tools=[session]),
        )
        return response.text or ""


# @@@SNIPEND
