from __future__ import annotations

from agents import Agent, Runner, trace
from agents.mcp import MCPServer
from agents.model_settings import ModelSettings
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
            workflow.logger.info("=== AVAILABLE PROMPTS ===")
            prompts_result = await server.list_prompts()
            workflow.logger.info("User can select from these prompts:")
            for i, prompt in enumerate(prompts_result.prompts, 1):
                workflow.logger.info(f"  {i}. {prompt.name} - {prompt.description}")
            workflow.logger.info("")

            # Demo code review with user-selected prompt
            workflow.logger.info("=== CODE REVIEW DEMO ===")

            # Get instructions from prompt
            workflow.logger.info(
                "Getting instructions from prompt: generate_code_review_instructions"
            )
            try:
                prompt_result = await server.get_prompt(
                    "generate_code_review_instructions",
                    {"focus": "security vulnerabilities", "language": "python"},
                )
                content = prompt_result.messages[0].content
                if hasattr(content, "text"):
                    instructions = content.text
                else:
                    instructions = str(content)
                workflow.logger.info("Generated instructions")
            except Exception as e:
                workflow.logger.info(f"Failed to get instructions: {e}")
                instructions = f"You are a helpful assistant. Error: {e}"

            agent = Agent(
                name="Code Reviewer Agent",
                instructions=instructions,
                model_settings=ModelSettings(tool_choice="auto"),
            )

            message = """Please review this code:

def process_user_input(user_input):
    command = f"echo {user_input}"
    os.system(command)
    return "Command executed"

"""

            workflow.logger.info(f"Running: {message[:60]}...")
            result = await Runner.run(starting_agent=agent, input=message)
            workflow.logger.info(result.final_output)
            workflow.logger.info("\n" + "=" * 50 + "\n")

            return "Prompt server demo completed successfully"
