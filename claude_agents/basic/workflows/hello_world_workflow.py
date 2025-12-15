"""Basic hello world workflow using Claude Agent SDK."""

from temporalio import workflow
from temporalio.contrib.claude_agent import (
    ClaudeMessageReceiver,
    ClaudeSessionConfig,
    SimplifiedClaudeClient,
    workflow as claude_workflow,
)


@workflow.defn
class HelloWorldAgent(ClaudeMessageReceiver):
    """Simple Claude workflow that responds in haikus."""

    @workflow.run
    async def run(self, prompt: str) -> str:
        """Execute the workflow with a Claude session.

        Args:
            prompt: The user's input prompt

        Returns:
            Claude's response
        """
        # Initialize the message receiver
        self.init_claude_receiver()

        # Configure Claude with haiku instruction
        config = ClaudeSessionConfig(
            system_prompt="You only respond in haikus.",
            max_turns=1,
        )

        # Create and use Claude session
        # The context manager handles activity lifecycle - when exiting, it waits
        # for the activity to complete gracefully before returning
        async with claude_workflow.claude_session("hello-session", config):
            # Create client for this workflow
            client = SimplifiedClaudeClient(self)

            # Send query and collect response
            result = ""
            async for message in client.send_query(prompt):
                workflow.logger.debug(f"Received message type: {message.get('type')}")

                # Extract text from assistant messages
                if message.get("type") == "assistant":
                    msg_content = message.get("message", {}).get("content", [])
                    for block in msg_content:
                        if block.get("type") == "text":
                            result += block.get("text", "")

            # Close the client (optional - kept for backwards compatibility)
            # Actual cleanup happens when exiting the context manager
            await client.close()

        return result