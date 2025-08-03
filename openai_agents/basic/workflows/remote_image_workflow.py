from agents import Agent, Runner
from temporalio import workflow


@workflow.defn
class RemoteImageWorkflow:
    @workflow.run
    async def run(
        self, image_url: str, question: str = "What do you see in this image?"
    ) -> str:
        """
        Process a remote image URL with an AI agent.

        Args:
            image_url: URL of the remote image
            question: Question to ask about the image

        Returns:
            Agent's response about the image
        """
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
                            "image_url": image_url,
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
