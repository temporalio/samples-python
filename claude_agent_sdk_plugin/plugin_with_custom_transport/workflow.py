from datetime import timedelta

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    CLIConnectionError,
    ResultMessage,
)
from temporalio import workflow
from temporalio.claude_agent_sdk import TemporalTransport

from claude_agent_sdk_plugin.plugin_with_custom_transport.connector import (
    SavedTurn,
    find_saved_turn,
)

# Where the Worker's connector puts the plugin, in Claude Code's sandbox. The
# path is recorded in history, as part of the connect Activity's input.
PLUGIN_DIR = "/home/agent/plugins/haiku-writer"

# Claude Code names plugin MCP tools mcp__plugin_<plugin>_<server>__<tool>.
COUNT_SYLLABLES = "mcp__plugin_haiku-writer_syllables__count_syllables"


@workflow.defn
class PluginWithCustomTransportWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        return await self.ask(prompt)

    def options(self, session_id: str, *, resume: bool) -> ClaudeAgentOptions:
        """Options that start the session, or resume it."""
        return ClaudeAgentOptions(
            plugins=[{"type": "local", "path": PLUGIN_DIR}],
            # Limit Claude Code's built-in tools to just Skill.
            tools=["Skill"],
            # Claude Code runs skills without asking, but MCP tools need allowing.
            allowed_tools=[COUNT_SYLLABLES],
            setting_sources=[],
            env={"CLAUDE_CODE_RESUME_INTERRUPTED_TURN": "1"},
            session_id=None if resume else session_id,
            resume=session_id if resume else None,
        )

    async def ask(self, prompt: str) -> str:
        """Answer the prompt, finishing the turn if the connection is lost."""
        session_id = str(workflow.uuid4())
        turn = SavedTurn(started=False, result=None)

        while True:
            try:
                options = self.options(session_id, resume=turn.started)
                transport = TemporalTransport(options)
                async with ClaudeSDKClient(
                    options=options, transport=transport
                ) as client:
                    # Send the prompt until Claude Code saves it. After that, a
                    # resume finishes the turn.
                    if not turn.started:
                        await client.query(prompt)

                    async for message in client.receive_response():
                        if isinstance(message, ResultMessage):
                            return message.result or "\n".join(message.errors or [])

                raise RuntimeError("Claude Code ended the turn without a result")

            except CLIConnectionError:
                # Claude Code may have finished the turn after the Worker's last
                # read. If so, its transcript in the sandbox has the answer.
                turn = await workflow.execute_activity(
                    find_saved_turn,
                    session_id,
                    start_to_close_timeout=timedelta(minutes=1),
                )
                if turn.result is not None:
                    return turn.result

                # Claude Code can't continue a session it didn't receive the
                # prompt for, so start a new one.
                if not turn.started:
                    session_id = str(workflow.uuid4())
