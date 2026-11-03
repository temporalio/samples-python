from dataclasses import dataclass, field

from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    CLIConnectionError,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
    UserMessage,
)
from temporalio import workflow
from temporalio.claude_agent_sdk import TemporalTransport

COORDINATOR = "coordinator"

AGENTS = {
    "researcher": AgentDefinition(
        description="Finds the key facts about a topic.",
        prompt="You are a researcher. Reply with a short list of key facts.",
        tools=["WebSearch", "WebFetch"],
    ),
    "writer": AgentDefinition(
        description="Turns notes into a short, readable briefing.",
        prompt="You are a writer. Turn the notes you are given into a briefing.",
        tools=[],
    ),
}


@dataclass
class Briefing:
    result: str
    messages_by_agent: dict[str, list[str]] = field(default_factory=dict)


# The text Claude Code sends itself to continue an interrupted turn.
CONTINUE = "Continue from where you left off."


@workflow.defn
class MultiAgentWorkflow:
    def __init__(self) -> None:
        self.roles: dict[str, str] = {}
        self.messages_by_agent: dict[str, list[str]] = {}

    @workflow.run
    async def run(self, topic: str) -> Briefing:
        prompt = (
            f"Write a short briefing on this topic: {topic}. Delegate the "
            "research to the researcher, then give the notes to the writer. "
            "Wait for each subagent's result before the next step (pass "
            "run_in_background: false)."
        )
        return await self.ask(prompt)

    def options(
        self, session_id: str | None = None, prompt_id: str | None = None
    ) -> ClaudeAgentOptions:
        """Options that start a new session, or redo the turn from prompt_id in session_id."""
        return ClaudeAgentOptions(
            agents=AGENTS,
            # Required to receive the prompt's UUID in the response stream.
            extra_args={"replay-user-messages": None},
            # A subagent's tools must also be listed here. "Agent" is the delegation
            # tool in this Claude Code version.
            tools=["Agent", "WebSearch", "WebFetch"],
            allowed_tools=["Agent", "WebSearch", "WebFetch"],
            permission_mode="default",
            # Forward the subagents' text, not only their tool calls.
            forward_subagent_text=True,
            setting_sources=[],
            resume=session_id if prompt_id else None,
            resume_session_at=prompt_id,
        )

    async def ask(self, prompt: str) -> Briefing:
        """Answer the prompt, redoing the turn if the connection is lost."""
        session_id = None  # Claude Code's, once it started
        prompt_id = None  # The prompt's, once Claude Code saved it

        while True:
            # The turn starts over, so record only its messages.
            self.roles, self.messages_by_agent = {}, {}
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
                        elif isinstance(message, AssistantMessage):
                            self.record(message)
                        elif isinstance(message, ResultMessage):
                            return Briefing(
                                message.result or "", self.messages_by_agent
                            )

                raise RuntimeError("Claude Code ended the turn without a result")

            except CLIConnectionError:
                # Redo the turn from the prompt if Claude Code saved it, or start again.
                pass

    def record(self, message: AssistantMessage) -> None:
        # A subagent's messages carry parent_tool_use_id, the Agent call that
        # started it.
        role = self.roles.get(message.parent_tool_use_id or "", COORDINATOR)
        for block in message.content:
            if isinstance(block, ToolUseBlock) and block.name == "Agent":
                self.roles[block.id] = block.input["subagent_type"]
            elif isinstance(block, TextBlock):
                workflow.logger.info("%s: %s", role, block.text)
                self.messages_by_agent.setdefault(role, []).append(block.text)
