from datetime import timedelta
from typing import Any

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    CLIConnectionError,
    ResultMessage,
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
    @workflow.init
    def __init__(self, prompt: str) -> None:
        # Chosen here, so the Workflow can resume the session even mid-turn.
        self.session_id = str(workflow.uuid4())
        self.client = self.new_client(session_id=self.session_id)

    @workflow.run
    async def run(self, prompt: str) -> str:
        await self.client.connect()
        try:
            await self.client.query(prompt)
            result = await self.reply()
        except CLIConnectionError:
            result = await self.resume()

        await self.client.disconnect()
        return result

    def new_client(
        self, *, session_id: str | None = None, resume: str | None = None
    ) -> ClaudeSDKClient:
        """A client that creates the session with session_id, or continues it with resume."""
        options = ClaudeAgentOptions(
            tools=[],
            mcp_servers={
                "demo": create_sdk_mcp_server("demo", tools=[count_letter, get_weather])
            },
            allowed_tools=["mcp__demo__count_letter", "mcp__demo__get_weather"],
            setting_sources=[],
            env={"CLAUDE_CODE_RESUME_INTERRUPTED_TURN": "1"},
            session_id=session_id,
            resume=resume,
        )
        return ClaudeSDKClient(options=options, transport=TemporalTransport(options))

    async def resume(self) -> str:
        """Resume the session until Claude Code finishes the cut-off turn."""
        while True:
            await self.client.disconnect()
            self.client = self.new_client(resume=self.session_id)
            try:
                await self.client.connect()
                return await self.reply()
            except CLIConnectionError:
                continue

    async def reply(self) -> str:
        async for message in self.client.receive_response():
            if isinstance(message, ResultMessage):
                return message.result or "\n".join(message.errors or [])
        return ""
