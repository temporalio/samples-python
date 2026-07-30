from __future__ import annotations

from agents import Agent, Runner, trace
from agents.mcp import MCPServer
from temporalio import workflow
from temporalio.contrib import openai_agents


@workflow.defn
class PromptServerWorkflow:
    @workflow.run
    async def run(self) -> str:
        with trace(workflow_name="Prompt Server Example"):
            outputs: list[str] = []
            server: MCPServer = openai_agents.workflow.stateless_mcp_server(
                "PromptServer"
            )

            # Show available prompts
            workflow.logger.info("=== AVAILABLE PROMPTS ===")
            outputs.append("=== AVAILABLE PROMPTS ===")
            prompts_result = await server.list_prompts()
            workflow.logger.info("User can select from these prompts:")
            outputs.append("User can select from these prompts:")
            for i, prompt in enumerate(prompts_result.prompts, 1):
                line = f"  {i}. {prompt.name} - {prompt.description}"
                workflow.logger.info(line)
                outputs.append(line)
            workflow.logger.info("")
            outputs.append("")

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
                instructions = (
                    content.text if hasattr(content, "text") else str(content)
                )
                workflow.logger.info("Generated instructions")
                preview = instructions[:200].replace("\n", " ") + (
                    "..." if len(instructions) > 200 else ""
                )
                outputs.append("=== INSTRUCTIONS (PREVIEW) ===")
                outputs.append(preview)
            except Exception as e:
                workflow.logger.info(f"Failed to get instructions: {e}")
                instructions = f"You are a helpful assistant. Error: {e}"
                outputs.append(f"Failed to get instructions: {e}")

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

            workflow.logger.info(f"Running: {message[:60]}...")
            outputs.append("=== REVIEW OUTPUT ===")
            result = await Runner.run(starting_agent=agent, input=message)
            workflow.logger.info(result.final_output)
            outputs.append(result.final_output)
            workflow.logger.info("\n" + "=" * 50 + "\n")
            return "\n".join(outputs)
