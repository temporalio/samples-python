from io import StringIO
from agents import Agent, Runner
from temporalio import workflow
from openai_agents.memory.postgres_session import PostgresSession, PostgresSessionConfig


@workflow.defn
class PostgresSessionWorkflow:
    @workflow.run
    async def run(self, session_id: str) -> str:
        # Create string buffer to capture all output
        output = StringIO()
        # Create a PostgreSQL session instance that will persist across runs
        postgres_config = PostgresSessionConfig(
            messages_table="session_messages",
            sessions_table="session",
            operation_id_sequence="session_operation_id_sequence",
        )
        session = PostgresSession(session_id=session_id, config=postgres_config)

        # Create an agent
        agent = Agent(
            name="Assistant",
            instructions="Reply very concisely.",
        )

        output.write("=== Session Example ===\n")
        output.write("The agent will remember previous messages automatically.\n\n")

        # First turn
        output.write("First turn:\n")
        output.write("User: What city is the Golden Gate Bridge in?\n")
        result = await Runner.run(
            agent,
            "What city is the Golden Gate Bridge in?",
            session=session,
        )
        output.write(f"Assistant: {result.final_output}\n\n")

        # Second turn - the agent will remember the previous conversation
        output.write("Second turn:\n")
        output.write("User: What state is it in?\n")
        result = await Runner.run(agent, "What state is it in?", session=session)
        output.write(f"Assistant: {result.final_output}\n\n")

        # Third turn - continuing the conversation
        output.write("Third turn:\n")
        output.write("User: What's the population of that state?\n")
        result = await Runner.run(
            agent,
            "What's the population of that state?",
            session=session,
        )
        output.write(f"Assistant: {result.final_output}\n\n")

        output.write("=== Conversation Complete ===\n")
        output.write(
            "Notice how the agent remembered the context from previous turns!\n"
        )
        output.write("Sessions automatically handles conversation history.\n")

        # Demonstrate the limit parameter - get only the latest 2 items
        output.write("\n=== Latest Items Demo ===\n")
        latest_items = await session.get_items(limit=2)
        output.write("Latest 2 items:\n")
        for i, msg in enumerate(latest_items, 1):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            output.write(f"  {i}. {role}: {content}\n")

        output.write(
            f"\nFetched {len(latest_items)} out of total conversation history.\n"
        )

        # Get all items to show the difference
        all_items = await session.get_items()
        output.write(f"Total items in session: {len(all_items)}\n")

        # Return the buffered output as a string
        return output.getvalue()
