from temporalio.client import Client, StreamConfig
from temporalio.worker import Worker
from temporalio_streams_redis import RedisStreamStore

from streams_redis.activities.model_activity import ANSWER, stream_answer
from streams_redis.run_agent import QUESTION, run
from streams_redis.shared import TASK_QUEUE, AgentEvent
from streams_redis.workflows.agent_workflow import AgentWorkflow


async def test_a_reader_resumes_at_its_offset(client: Client, redis_url: str):
    config = client.config()
    config["stream_config"] = StreamConfig(stores=[RedisStreamStore(redis_url)])

    async def connect() -> Client:
        return Client(**config)

    async with Worker(
        await connect(),
        task_queue=TASK_QUEUE,
        workflows=[AgentWorkflow],
        activities=[stream_answer],
    ):
        events = await run(connect)

    # The reader got each event once and in order, across its disconnect, to the close.
    assert events == [
        AgentEvent("status", f"Thinking about: {QUESTION}"),
        *(AgentEvent("token", word) for word in ANSWER.split()),
        AgentEvent("status", "Done"),
    ]
