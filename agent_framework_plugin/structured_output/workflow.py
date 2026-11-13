"""Typed output: the agent fills a Pydantic model and the Workflow returns it."""

# @@@SNIPSTART python-agent-framework-structured-output-workflow
from datetime import timedelta

from agent_framework import Agent
from pydantic import BaseModel, Field
from temporalio import workflow
from temporalio.agent_framework import TemporalChatClient
from temporalio.exceptions import ApplicationError


class PersonInfo(BaseModel):
    name: str = Field(description="Name of the person")
    age: int = Field(description="Age of the person")
    occupation: str = Field(description="Occupation of the person")


@workflow.defn
class StructuredOutputWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> PersonInfo:
        agent = Agent(
            client=TemporalChatClient(
                "gpt-4o-mini", start_to_close_timeout=timedelta(seconds=60)
            ),
            instructions="Extract the person's details from the text.",
        )
        # The model's JSON schema crosses to the Activity; the Workflow parses the reply.
        response = await agent.run(prompt, options={"response_format": PersonInfo})
        person = response.value
        if not isinstance(person, PersonInfo):
            raise ApplicationError(
                "The model did not return a PersonInfo", non_retryable=True
            )
        return person


# @@@SNIPEND
