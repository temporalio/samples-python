from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    CLIConnectionError,
    ResultMessage,
    SystemMessage,
    UserMessage,
)
from temporalio import workflow
from temporalio.claude_agent_sdk import TemporalTransport

# Where the Worker's connector puts the plugin, in Claude Code's sandbox. The
# path is recorded in history, as part of the connect Activity's input.
PLUGIN_DIR = "/home/agent/plugins/haiku-writer"

# The text Claude Code sends itself to continue an interrupted turn.
CONTINUE = "Continue from where you left off."

# Claude Code names plugin MCP tools mcp__plugin_<plugin>_<server>__<tool>.
COUNT_SYLLABLES = "mcp__plugin_haiku-writer_syllables__count_syllables"


@workflow.defn
class PluginWithCustomTransportWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        return await self.ask(prompt)

    def options(
        self, session_id: str | None = None, prompt_id: str | None = None
    ) -> ClaudeAgentOptions:
        """Options that start a new session, or redo the turn from prompt_id in session_id."""
        return ClaudeAgentOptions(
            plugins=[{"type": "local", "path": PLUGIN_DIR}],
            # Limit Claude Code's built-in tools to just Skill.
            tools=["Skill"],
            # Claude Code runs skills without asking, but MCP tools need allowing.
            allowed_tools=[COUNT_SYLLABLES],
            setting_sources=[],
            # Required to receive the prompt's UUID in the response stream.
            extra_args={"replay-user-messages": None},
            resume=session_id if prompt_id else None,
            resume_session_at=prompt_id,
        )

    async def ask(self, prompt: str) -> str:
        """Answer the prompt, redoing the turn if the connection is lost."""
        session_id = None  # Claude Code's, once it started
        prompt_id = None  # The prompt's, once Claude Code saved it

        while True:
            try:
                options = self.options(session_id, prompt_id)
                transport = TemporalTransport(options)
                async with ClaudeSDKClient(
                    options=options, transport=transport
                ) as client:
                    await client.query(CONTINUE if prompt_id else prompt)

                    async for message in client.receive_response():
                        if (
                            isinstance(message, SystemMessage)
                            and message.subtype == "init"
                        ):
                            session_id = message.data["session_id"]
                        elif (
                            isinstance(message, UserMessage)
                            and message.uuid
                            and not prompt_id
                        ):
                            prompt_id = message.uuid
                        elif isinstance(message, ResultMessage):
                            return message.result or "\n".join(message.errors or [])

                raise RuntimeError("Claude Code ended the turn without a result")

            except CLIConnectionError:
                # Redo the turn from the prompt if Claude Code saved it, or start again.
                pass
