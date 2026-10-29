from datetime import timedelta
from typing import Any

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    CLIConnectionError,
    ResultMessage,
    SystemMessage,
    create_sdk_mcp_server,
    tool,
)
from temporalio import activity, workflow
from temporalio.claude_agent_sdk import TemporalTransport


@activity.defn
async def fetch_weather(city: str) -> str:
    return f"It is 21 C and sunny in {city}."


@tool(
    "count_letter",
    "Count how often a letter appears in a word",
    {"word": str, "letter": str},
)
async def count_letter(args: dict[str, Any]) -> dict[str, Any]:
    count = args["word"].lower().count(args["letter"].lower())
    return {"content": [{"type": "text", "text": str(count)}]}


@tool("get_weather", "Get the current weather in a city", {"city": str})
async def get_weather(args: dict[str, Any]) -> dict[str, Any]:
    weather = await workflow.execute_activity(
        fetch_weather, args["city"], start_to_close_timeout=timedelta(seconds=30)
    )
    return {"content": [{"type": "text", "text": weather}]}


@workflow.defn
class ToolsWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        return await self.ask(prompt)

    def options(self, *, resume: str | None = None) -> ClaudeAgentOptions:
        """Options that start a new session, or continue the one given by resume."""
        return ClaudeAgentOptions(
            tools=[],
            mcp_servers={
                "demo": create_sdk_mcp_server("demo", tools=[count_letter, get_weather])
            },
            allowed_tools=["mcp__demo__count_letter", "mcp__demo__get_weather"],
            setting_sources=[],
            env={"CLAUDE_CODE_RESUME_INTERRUPTED_TURN": "1"},
            resume=resume,
        )

    async def ask(self, prompt: str) -> str:
        """Answer the prompt, resuming the session if the connection is lost."""
        session_id = None  # Claude Code's, once it has the prompt

        while True:
            try:
                options = self.options(resume=session_id)
                transport = TemporalTransport(options)
                async with ClaudeSDKClient(
                    options=options, transport=transport
                ) as client:
                    # Keep sending the prompt until Claude Code reports a session, which
                    # means it received it. After that, a resume finishes the turn.
                    if session_id is None:
                        await client.query(prompt)

                    async for message in client.receive_response():
                        if (
                            isinstance(message, SystemMessage)
                            and message.subtype == "init"
                        ):
                            session_id = message.data["session_id"]
                        elif isinstance(message, ResultMessage):
                            return message.result or "\n".join(message.errors or [])

                raise RuntimeError("Claude Code ended the turn without a result")

            except CLIConnectionError:
                # Resume the session if Claude Code started it, or start again.
                pass
