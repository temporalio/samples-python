"""Structured output: agent returns a typed Pydantic model.

``TemporalAgent(structured_output_model=PersonInfo)`` makes Strands coerce the
model's final response into an instance of ``PersonInfo``. The plugin installs
``pydantic_data_converter`` by default, so the typed value flows back across
the activity/workflow boundary without extra wiring.
"""

from datetime import timedelta

from pydantic import BaseModel, Field
from temporalio import workflow
from temporalio.contrib.strands import TemporalAgent


class PersonInfo(BaseModel):
    name: str = Field(description="Name of the person")
    age: int = Field(description="Age of the person")
    occupation: str = Field(description="Occupation of the person")


@workflow.defn
class StructuredOutputWorkflow:
    def __init__(self) -> None:
        self.agent = TemporalAgent(
            start_to_close_timeout=timedelta(seconds=60),
            structured_output_model=PersonInfo,
        )

    @workflow.run
    async def run(self, prompt: str) -> PersonInfo:
        result = await self.agent.invoke_async(prompt)
        assert isinstance(result.structured_output, PersonInfo)
        return result.structured_output
