from agents import Agent, Runner
from temporalio import workflow

from openai_agents.basic.activities.image_activities import read_image_as_base64


@workflow.defn
class LocalImageWorkflow:
    @workflow.run
    async def run(
        self, image_path: str, question: str = "What do you see in this image?"
    ) -> str:
        """
        Process a local image file with an AI agent.

        Args:
            image_path: Path to the local image file
            question: Question to ask about the image

        Returns:
            Agent's response about the image
        """
        # Convert image to base64 using activity
        b64_image = await workflow.execute_activity(
            read_image_as_base64,
            image_path,
            start_to_close_timeout=workflow.timedelta(seconds=30),
        )

        agent = Agent(
            name="Assistant",
            instructions="You are a helpful assistant.",
        )

        result = await Runner.run(
            agent,
            [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_image",
                            "detail": "auto",
                            "image_url": f"data:image/jpeg;base64,{b64_image}",
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": question,
                },
            ],
        )
        return result.final_output
