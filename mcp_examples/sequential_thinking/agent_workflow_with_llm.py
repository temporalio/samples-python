"""Agent workflow that uses an LLM with the sequential thinking MCP tool."""

from datetime import timedelta
from typing import Any, Dict, List

from temporalio import workflow

from mcp_examples.common.mcp_server_nexus_service import MCPServerNexusService

from .nexus_client import NexusMCPClientSession

with workflow.unsafe.imports_passed_through():
    from .llm_activity import LLMRequest, call_llm, parse_json_response


@workflow.defn(sandboxed=False)
class AgentWorkflowWithLLM:
    """Agent workflow that uses an LLM to solve problems with sequential thinking."""

    @workflow.run
    async def run(self, problem: str) -> str:
        """
        Run the agent workflow to solve a problem using sequential thinking.

        Args:
            problem: The problem or question to solve

        Returns:
            The final solution or answer
        """
        # Create MCP client
        nexus_client = workflow.create_nexus_client(
            service=MCPServerNexusService,
            endpoint="mcp-sequential-thinking-nexus-endpoint",
        )
        mcp = NexusMCPClientSession(nexus_client)
        await mcp.initialize()

        # System prompt for the LLM
        system_prompt = """You are a problem-solving assistant that uses sequential thinking to break down complex problems.
        
You have access to a 'sequentialthinking' tool that helps you think through problems step by step.
Each thought should build on previous thoughts, and you can revise or branch your thinking as needed.

When generating thoughts:
1. Be clear and specific in each thought
2. Build logically on previous thoughts
3. Feel free to revise if you realize a mistake
4. Continue until you reach a satisfactory solution
5. Set nextThoughtNeeded to false only when you have the final answer

Always respond with valid JSON containing the parameters for the sequentialthinking tool."""

        # Initialize variables for the thinking loop
        thought_number = 1
        total_thoughts = 3  # Initial estimate
        thoughts_history: List[Dict[str, Any]] = []

        # Start the thinking loop
        while True:
            # Prepare context for the LLM
            context = self._build_context(
                problem, thoughts_history, thought_number, total_thoughts
            )

            # Call LLM to generate the next thought
            llm_response = await workflow.execute_activity(
                call_llm,
                LLMRequest(
                    system_prompt=system_prompt,
                    user_prompt=context,
                    temperature=0.7,
                    max_tokens=500,
                    model="claude-3-5-sonnet-20241022",  # Override default
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )

            # Parse the JSON response
            thought_params = await workflow.execute_activity(
                parse_json_response,
                llm_response.content,
                start_to_close_timeout=timedelta(seconds=5),
            )

            # Ensure required fields are present
            thought_params.setdefault("thoughtNumber", thought_number)
            thought_params.setdefault("totalThoughts", total_thoughts)

            # Store the thought
            thoughts_history.append(thought_params)

            # Call the sequential thinking tool
            _ = await mcp.call_tool("sequentialthinking", arguments=thought_params)

            # Check if we need more thoughts
            if not thought_params.get("nextThoughtNeeded", True):
                # We're done - extract the final answer
                final_answer = thought_params.get("thought", "No answer generated")
                break

            # Update counters for next iteration
            thought_number += 1
            if thought_number > total_thoughts:
                total_thoughts = thought_number + 2  # Extend if needed

        # Return the complete solution
        return self._format_solution(problem, thoughts_history, final_answer)

    def _build_context(
        self,
        problem: str,
        thoughts_history: List[Dict[str, Any]],
        thought_number: int,
        total_thoughts: int,
    ) -> str:
        """Build context for the LLM including the problem and thought history."""
        context = f"Problem to solve: {problem}\n\n"

        if thoughts_history:
            context += "Previous thoughts:\n"
            for i, thought in enumerate(thoughts_history, 1):
                context += f"{i}. {thought['thought']}\n"
            context += "\n"

        context += f"Now generate thought #{thought_number} (estimated {total_thoughts} total thoughts needed).\n"
        context += (
            "Respond with JSON for the sequentialthinking tool with these fields:\n"
        )
        context += "- thought: Your current thinking step\n"
        context += "- nextThoughtNeeded: Whether another thought is needed (boolean)\n"
        context += "- thoughtNumber: Current thought number\n"
        context += "- totalThoughts: Estimated total thoughts needed\n"
        context += "- (optional) isRevision, revisesThought, branchFromThought, branchId, needsMoreThoughts\n"

        return context

    def _format_solution(
        self, problem: str, thoughts_history: List[Dict[str, Any]], final_answer: str
    ) -> str:
        """Format the complete solution with the thinking process."""
        solution = f"Problem: {problem}\n\n"
        solution += "Thinking Process:\n"
        solution += "=" * 50 + "\n"

        for thought in thoughts_history:
            solution += f"\nThought #{thought['thoughtNumber']}:\n"
            solution += f"{thought['thought']}\n"

            if thought.get("isRevision"):
                solution += f"(This revises thought #{thought.get('revisesThought')})\n"

            if thought.get("branchFromThought"):
                solution += f"(Branching from thought #{thought['branchFromThought']}, "
                solution += f"branch: {thought.get('branchId', 'main')})\n"

        solution += "\n" + "=" * 50 + "\n"
        solution += f"Final Answer: {final_answer}\n"

        return solution
