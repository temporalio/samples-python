from google.adk import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.utils.context_utils import Aclosing
from google.genai import types
from temporalio import workflow
from temporalio.contrib.google_adk_agents import TemporalMcpToolSet, TemporalModel

from google_adk_agents.mcp.toolsets import echo_toolset


# @@@SNIPSTART google-adk-agents-mcp-echo-mcp-workflow
@workflow.defn
class EchoMcpWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        # TemporalMcpToolSet runs the MCP server's list-tools and call-tool
        # calls as activities (the provider names them echo-list-tools and
        # echo-call-tool on the worker). The not_in_workflow_toolset factory
        # lets you run this same agent locally, outside a workflow, by hitting
        # the MCP server directly.
        agent = Agent(
            name="echo_agent",
            model=TemporalModel("gemini-2.5-flash"),
            instruction="Use the echo tool to echo back the user's message.",
            tools=[TemporalMcpToolSet("echo", not_in_workflow_toolset=echo_toolset)],
        )

        session_service = InMemorySessionService()
        session = await session_service.create_session(
            app_name="echo_app", user_id="user"
        )

        runner = Runner(
            agent=agent,
            app_name="echo_app",
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
