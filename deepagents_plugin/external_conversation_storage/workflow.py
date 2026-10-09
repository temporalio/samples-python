"""A multi-turn agent that loads its full S3 transcript on each turn."""

from dataclasses import dataclass
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.common import RetryPolicy
from temporalio.deepagents import create_temporal_deep_agent

MODEL = "fake:external-conversation-storage"
TASK_QUEUE = "deepagents-external-conversation-storage"
S3_BUCKET = "temporal-payloads"


@dataclass
class Turn:
    user: str
    assistant: str


@dataclass
class ConversationResult:
    last_answer: str
    turns: int
    first_context_chars: int
    last_context_chars: int
    transcript_turns: int


def _conversation_prefix(workflow_id: str) -> str:
    """Keep user-provided workflow IDs out of S3 key syntax."""
    import hashlib

    return f"conversation-memory/{hashlib.sha256(workflow_id.encode()).hexdigest()}/"


@activity.defn
async def load_conversation_history(workflow_id: str, turn_index: int) -> list[Turn]:
    """Read every earlier exchange from the external transcript."""
    import aioboto3

    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url="http://localhost:5000",
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1",
    ) as client:
        turns = []
        prefix = _conversation_prefix(workflow_id)
        for index in range(turn_index):
            response = await client.get_object(
                Bucket=S3_BUCKET, Key=f"{prefix}turn-{index:08d}.json"
            )
            import json

            turns.append(Turn(**json.loads(await response["Body"].read())))
        return turns


@activity.defn
async def save_turn(workflow_id: str, turn_index: int, turn: Turn) -> None:
    """Append one exchange as its own immutable S3 object."""
    import json
    from dataclasses import asdict

    import aioboto3

    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url="http://localhost:5000",
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1",
    ) as client:
        await client.put_object(
            Bucket=S3_BUCKET,
            Key=f"{_conversation_prefix(workflow_id)}turn-{turn_index:08d}.json",
            Body=json.dumps(asdict(turn)).encode(),
            ContentType="application/json",
        )


@workflow.defn
class StoredConversationAgent:
    def __init__(self) -> None:
        self.pending_turns: list[str] = []
        self.finished = False

    @workflow.signal
    def submit_turn(self, question: str) -> None:
        self.pending_turns.append(question)

    @workflow.signal
    def finish(self) -> None:
        self.finished = True

    @workflow.run
    async def run(self) -> ConversationResult:
        workflow_id = workflow.info().workflow_id
        turn_count = 0
        first_context_chars = 0
        last_context_chars = 0
        last_answer = ""

        while True:
            await workflow.wait_condition(
                lambda: bool(self.pending_turns) or self.finished
            )
            if not self.pending_turns:
                break
            question = self.pending_turns.pop(0)
            turn_index = turn_count
            history = await workflow.execute_activity(
                load_conversation_history,
                args=[workflow_id, turn_index],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=1),
            )
            memory = "\n".join(
                f"User: {turn.user}\nAssistant: {turn.assistant}" for turn in history
            )
            system_prompt = (
                "Answer the user's latest message. Use the full conversation "
                "when relevant. This is the complete conversation so far.\n\n"
                "Conversation history:\n"
                f"{memory or '(no earlier turns)'}"
            )
            # A fresh agent invocation receives the complete prior transcript
            # and current prompt; prior turns are not carried in graph state.
            agent = create_temporal_deep_agent(
                model=MODEL,
                system_prompt=system_prompt,
                activity_options={"start_to_close_timeout": timedelta(seconds=30)},
            )
            context_chars = len(system_prompt) + len(question)
            if turn_count == 0:
                first_context_chars = context_chars
            result = await agent.ainvoke(
                {"messages": [{"role": "user", "content": question}]}
            )
            answer = result["messages"][-1].content
            if not isinstance(answer, str):
                raise TypeError("Expected a text response from the model")
            last_answer = answer
            last_context_chars = context_chars
            await workflow.execute_activity(
                save_turn,
                args=[workflow_id, turn_index, Turn(user=question, assistant=answer)],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=1),
            )
            turn_count += 1

        return ConversationResult(
            last_answer=last_answer,
            turns=turn_count,
            first_context_chars=first_context_chars,
            last_context_chars=last_context_chars,
            transcript_turns=turn_count,
        )
