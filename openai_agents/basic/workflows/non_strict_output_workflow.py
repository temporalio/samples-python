import json
from dataclasses import dataclass
from typing import Any

from agents import Agent, AgentOutputSchema, AgentOutputSchemaBase, Runner
from temporalio import workflow


@dataclass
class OutputType:
    jokes: dict[int, str]
    """A list of jokes, indexed by joke number."""


class CustomOutputSchema(AgentOutputSchemaBase):
    """A demonstration of a custom output schema."""

    def is_plain_text(self) -> bool:
        return False

    def name(self) -> str:
        return "CustomOutputSchema"

    def json_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "jokes": {"type": "object", "properties": {"joke": {"type": "string"}}}
            },
        }

    def is_strict_json_schema(self) -> bool:
        return False

    def validate_json(self, json_str: str) -> Any:
        json_obj = json.loads(json_str)
        # Just for demonstration, we'll return a list.
        return list(json_obj["jokes"].values())


@workflow.defn
class NonStrictOutputWorkflow:
    @workflow.run
    async def run(self, input_text: str) -> dict[str, Any]:
        """
        Demonstrates non-strict output types that require special handling.

        Args:
            input_text: The input message to the agent

        Returns:
            Dictionary with results from different output type approaches
        """
        results = {}

        agent = Agent(
            name="Assistant",
            instructions="You are a helpful assistant.",
            output_type=OutputType,
        )

        # First, try with strict output type (this should fail)
        try:
            result = await Runner.run(agent, input_text)
            results["strict_result"] = "Unexpected success"
        except Exception as e:
            results["strict_error"] = str(e)

        # Now try with non-strict output type
        try:
            agent.output_type = AgentOutputSchema(OutputType, strict_json_schema=False)
            result = await Runner.run(agent, input_text)
            results["non_strict_result"] = result.final_output
        except Exception as e:
            results["non_strict_error"] = str(e)

        # Finally, try with custom output type
        # Not presently supported by Temporal
        # try:
        #     agent.output_type = CustomOutputSchema()
        #     result = await Runner.run(agent, input_text)
        #     results["custom_result"] = result.final_output
        # except Exception as e:
        #     results["custom_error"] = str(e)

        return results
