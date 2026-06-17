from google.adk import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.utils.context_utils import Aclosing
from google.genai import types
from temporalio import workflow
from temporalio.contrib.google_adk_agents import TemporalMcpToolSet, TemporalModel

from google_adk_agents.mcp.toolsets import filesystem_toolset


# @@@SNIPSTART google-adk-agents-mcp-filesystem-mcp-workflow
@workflow.defn
class FilesystemMcpWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        # TemporalMcpToolSet runs the MCP server's list-tools / call-tool
        # operations as activities (named "filesystem-list-tools" /
        # "filesystem-call-tool" by the provider on the worker). The
        # not_in_workflow_toolset factory lets the same agent run locally,
        # outside a workflow, by talking to the MCP server directly.
        agent = Agent(
            name="filesystem_agent",
            model=TemporalModel("gemini-2.5-flash"),
            instruction="Use your tools to answer questions about files.",
            tools=[
                TemporalMcpToolSet(
                    "filesystem", not_in_workflow_toolset=filesystem_toolset
                )
            ],
        )

        session_service = InMemorySessionService()
        session = await session_service.create_session(
            app_name="filesystem_app", user_id="user"
        )

        runner = Runner(
            agent=agent,
            app_name="filesystem_app",
            session_service=session_service,
        )

        final_text = ""
        async with Aclosing(
            runner.run_async(
                user_id="user",
                session_id=session.id,
                new_message=types.Content(role="user", parts=[types.Part(text=prompt)]),
            )
        ) as agen:
            async for event in agen:
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            final_text = part.text

        return final_text


# @@@SNIPEND
