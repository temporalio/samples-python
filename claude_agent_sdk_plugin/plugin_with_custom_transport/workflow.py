from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    CLIConnectionError,
    ResultMessage,
)
from temporalio import workflow
from temporalio.claude_agent_sdk import TemporalTransport

# Where the Worker's connector puts the plugin, in Claude Code's sandbox. The
# path is recorded in history, as part of the connect Activity's input.
PLUGIN_DIR = "/home/agent/plugins/haiku-writer"

# Claude Code names plugin MCP tools mcp__plugin_<plugin>_<server>__<tool>.
COUNT_SYLLABLES = "mcp__plugin_haiku-writer_syllables__count_syllables"


@workflow.defn
class PluginWithCustomTransportWorkflow:
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
            plugins=[{"type": "local", "path": PLUGIN_DIR}],
            # Limit Claude Code's built-in tools to just Skill.
            tools=["Skill"],
            # Claude Code runs skills without asking, but MCP tools need allowing.
            allowed_tools=[COUNT_SYLLABLES],
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
