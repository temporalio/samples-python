import json
from dataclasses import asdict, dataclass, field

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
# The same agents, as the Claude Agent SDK sends them to Claude Code.
AGENTS_JSON = {
    name: {key: value for key, value in asdict(agent).items() if value is not None}
    for name, agent in AGENTS.items()
}


@dataclass
class Briefing:
    result: str
    messages_by_agent: dict[str, list[str]] = field(default_factory=dict)


@workflow.defn
class MultiAgentWorkflow:
    def __init__(self) -> None:
        # Kept across resumes, so a resumed session adds to them.
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

    def options(self, resume: str | None = None) -> ClaudeAgentOptions:
        """Options that start a new session, or resume the one with this ID."""
        return ClaudeAgentOptions(
            agents=AGENTS,
            # A resumed Claude Code finishes the cut-off turn before it reads the
            # agents above or the forward_subagent_text request, so give both on
            # the command line too.
            extra_args={
                "agents": json.dumps(AGENTS_JSON),
                "forward-subagent-text": None,
            },
            # A subagent's tools must also be listed here. "Agent" is the delegation
            # tool in this Claude Code version.
            tools=["Agent", "WebSearch", "WebFetch"],
            allowed_tools=["Agent", "WebSearch", "WebFetch"],
            permission_mode="default",
            # Forward the subagents' text, not only their tool calls.
            forward_subagent_text=True,
            setting_sources=[],
            env={"CLAUDE_CODE_RESUME_INTERRUPTED_TURN": "1"},
            resume=resume,
        )

    async def ask(self, prompt: str) -> Briefing:
        """Answer the prompt in a session, resuming it if the connection is lost."""
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
                        elif isinstance(message, AssistantMessage):
                            self.record(message)
                        elif isinstance(message, ResultMessage):
                            return Briefing(
                                message.result or "", self.messages_by_agent
                            )

                raise RuntimeError("Claude Code ended the turn without a result")

            except CLIConnectionError:
                # Resume the session if Claude Code started it, or start again.
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
