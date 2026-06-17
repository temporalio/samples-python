from google.adk import Agent
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import InMemoryRunner
from google.genai import types
from temporalio import workflow
from temporalio.contrib.google_adk_agents import TemporalModel
from temporalio.contrib.workflow_streams import WorkflowStream


# @@@SNIPSTART google-adk-agents-streaming-streaming-agent-workflow
@workflow.defn
class StreamingAgentWorkflow:
    @workflow.init
    def __init__(self, prompt: str) -> None:
        # The workflow hosts a WorkflowStream. The streaming model activity
        # publishes raw LlmResponse chunks to it as they arrive from the model.
        self.stream = WorkflowStream()

    @workflow.run
    async def run(self, prompt: str) -> str:
        # streaming_topic selects the stream topic the chunks are published to.
        # RunConfig(streaming_mode=SSE) tells ADK to invoke the model with
        # streaming, which routes through the invoke_model_streaming activity.
        model = TemporalModel("gemini-2.5-flash", streaming_topic="responses")
        agent = Agent(
            name="streaming_agent",
            model=model,
            instruction="You are a helpful assistant.",
        )

        runner = InMemoryRunner(agent=agent, app_name="streaming_app")
        session = await runner.session_service.create_session(
            app_name="streaming_app", user_id="user"
        )

        final_text = ""
        async for event in runner.run_async(
            user_id="user",
            session_id=session.id,
            new_message=types.Content(role="user", parts=[types.Part(text=prompt)]),
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        final_text = part.text

        return final_text


# @@@SNIPEND
