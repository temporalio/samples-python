from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from agents import Agent, ImageGenerationTool, Runner
from temporalio import workflow


@dataclass
class ImageGenerationResult:
    final_output: str
    image_data: Optional[str] = None


@workflow.defn
class ImageGeneratorWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> ImageGenerationResult:
        agent = Agent(
            name="Image generator",
            instructions="You are a helpful agent.",
            tools=[
                ImageGenerationTool(
                    tool_config={"type": "image_generation", "quality": "low"},
                )
            ],
        )

        result = await Runner.run(agent, prompt)

        # Extract image data if available
        image_data = None
        for item in result.new_items:
            if (
                item.type == "tool_call_item"
                and item.raw_item.type == "image_generation_call"
                and (img_result := item.raw_item.result)
            ):
                image_data = img_result
                break

        return ImageGenerationResult(
            final_output=result.final_output, image_data=image_data
        )
