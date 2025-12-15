"""Workflow demonstrating tool usage with Claude Agent SDK."""

from datetime import timedelta

from temporalio import workflow
from temporalio.contrib.claude_agent import (
    ClaudeMessageReceiver,
    ClaudeSessionConfig,
    SimplifiedClaudeClient,
    workflow as claude_workflow,
)

from claude_agents.basic.activities.get_weather_activity import get_weather


@workflow.defn
class ToolsWorkflow(ClaudeMessageReceiver):
    """Claude workflow that can use tools (activities) to answer questions."""

    @workflow.run
    async def run(self, question: str) -> str:
        """Execute the workflow with tool support.

        Args:
            question: The user's question (e.g., "What's the weather in San Francisco?")

        Returns:
            Claude's response using the available tools
        """
        # Initialize the message receiver
        self.init_claude_receiver()

        # Configure Claude with tool support
        # Note: In the current implementation, tools are configured via allowed_tools
        # and Claude can invoke them through its built-in tool capabilities
        config = ClaudeSessionConfig(
            system_prompt="""You are a helpful agent with access to tools.
            When asked about weather, you can get real weather data for any city.
            Always use the weather tool when asked about weather conditions.""",
            max_turns=3,  # Allow multiple turns for tool usage
            allowed_tools=["get_weather"],  # List of allowed tools
        )

        # Create and use Claude session
        # The context manager handles activity lifecycle - when exiting, it waits
        # for the activity to complete gracefully before returning
        async with claude_workflow.claude_session("tools-session", config):
            # Create client for this workflow
            client = SimplifiedClaudeClient(self)

            # First, we need to handle the activity as a tool
            # In the actual implementation, this would be handled by the session
            # For now, we'll demonstrate the pattern

            # Check if the question is about weather
            if "weather" in question.lower():
                # Extract city from question (simple pattern matching)
                # In a real implementation, Claude would handle this
                import re
                city_match = re.search(r'in (\w+(?:\s+\w+)*)', question, re.IGNORECASE)
                city = city_match.group(1) if city_match else "San Francisco"

                # Execute the weather activity
                weather_data = await workflow.execute_activity(
                    get_weather,
                    city,
                    start_to_close_timeout=timedelta(seconds=10),
                )

                # Format the weather data for Claude
                weather_context = f"""
                Weather data for {weather_data.city}:
                - Temperature: {weather_data.temperature_range}
                - Conditions: {weather_data.conditions}

                Please provide a helpful response about the weather based on this data.
                Original question: {question}
                """

                # Send to Claude with the weather context
                query = weather_context
            else:
                # Send the original question
                query = question

            # Send query and collect response
            result = ""
            async for message in client.send_query(query):
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