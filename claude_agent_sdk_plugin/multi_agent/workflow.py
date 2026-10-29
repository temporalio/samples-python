from dataclasses import dataclass, field

from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    CLIConnectionError,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)
from temporalio import workflow
from temporalio.claude_agent_sdk import TemporalTransport

COORDINATOR = "coordinator"


@dataclass
class Briefing:
    result: str
    messages_by_agent: dict[str, list[str]] = field(default_factory=dict)


@workflow.defn
class MultiAgentWorkflow:
    @workflow.init
    def __init__(self, topic: str) -> None:
        # Chosen here, so the Workflow can resume the session even mid-turn.
        self.session_id = str(workflow.uuid4())
        # Kept across resumes, so a resumed session adds to them.
        self.roles: dict[str, str] = {}
        self.messages_by_agent: dict[str, list[str]] = {}
        self.client = self.new_client(session_id=self.session_id)

    @workflow.run
    async def run(self, topic: str) -> Briefing:
        await self.client.connect()
        try:
            await self.client.query(
                (
                    "Delegate the research to the researcher, then have the "
                    f"writer draft a short briefing on this topic: {topic}"
                )
            )
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
            agents={
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
            session_id=session_id,
            resume=resume,
        )
        return ClaudeSDKClient(options=options, transport=TemporalTransport(options))

    async def resume(self) -> Briefing:
        """Resume the session until Claude Code finishes the cut-off turn."""
        while True:
            await self.client.disconnect()
            self.client = self.new_client(resume=self.session_id)
            try:
                await self.client.connect()
                return await self.reply()
            except CLIConnectionError:
                continue

    async def reply(self) -> Briefing:
        async for message in self.client.receive_response():
            if isinstance(message, AssistantMessage):
                self.record(message)
            elif isinstance(message, ResultMessage):
                return Briefing(message.result or "", self.messages_by_agent)
        return Briefing("", self.messages_by_agent)

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
