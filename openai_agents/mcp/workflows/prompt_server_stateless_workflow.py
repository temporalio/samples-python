from __future__ import annotations

from agents import Agent, Runner, trace
from agents.mcp import MCPServer
from temporalio import workflow
from temporalio.contrib import openai_agents


@workflow.defn
class PromptServerWorkflow:
    @workflow.run
    async def run(self) -> str:
        with trace(workflow_name="MCP Prompt Server Example"):
            server: MCPServer = openai_agents.workflow.stateless_mcp_server(
                "PromptServer"
            )

            # Show available prompts
            print("=== AVAILABLE PROMPTS ===")
            prompts_result = await server.list_prompts()
            print("User can select from these prompts:")
            for i, prompt in enumerate(prompts_result.prompts, 1):
                print(f"  {i}. {prompt.name} - {prompt.description}")
            print()

            # Demo code review with user-selected prompt
            print("=== CODE REVIEW DEMO ===")

            # Get instructions from prompt
            print("Getting instructions from prompt: generate_code_review_instructions")
            try:
                prompt_result = await server.get_prompt("generate_code_review_instructions", {
                    "focus": "security vulnerabilities",
                    "language": "python"
                })
                content = prompt_result.messages[0].content
                if hasattr(content, "text"):
                    instructions = content.text
                else:
                    instructions = str(content)
                print("Generated instructions")
            except Exception as e:
                print(f"Failed to get instructions: {e}")
                instructions = f"You are a helpful assistant. Error: {e}"

            agent = Agent(
                name="Code Reviewer Agent",
                instructions=instructions,
            )

            message = """Please review this code:

def process_user_input(user_input):
    command = f"echo {user_input}"
    os.system(command)
    return "Command executed"

"""

            print(f"Running: {message[:60]}...")
            result = await Runner.run(starting_agent=agent, input=message)
            print(result.final_output)
            print("\n" + "=" * 50 + "\n")

            return "Prompt server demo completed successfully"