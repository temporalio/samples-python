"""
This is the Sequential Thinking example MCP Server
https://github.com/modelcontextprotocol/servers/tree/main/src/sequentialthinking
implemented as a Temporal workflow in Python.

The Sequential Thinking MCP server is an example of a stateful MCP server (i.e. it retains state
between successive tool invocations). Implemented as a Temporal workflow, this state is durable.
"""

import json
from typing import Any

from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    TextContent,
    Tool,
)
from temporalio import workflow

# Tool definition from the TypeScript reference server
# https://github.com/modelcontextprotocol/servers/tree/main/src/sequentialthinking
SEQUENTIAL_THINKING_TOOL = Tool(
    name="sequentialthinking",
    description="""A detailed tool for dynamic and reflective problem-solving through thoughts.
This tool helps analyze problems through a flexible thinking process that can adapt and evolve.
Each thought can build on, question, or revise previous insights as understanding deepens.

When to use this tool:
- Breaking down complex problems into steps
- Planning and design with room for revision
- Analysis that might need course correction
- Problems where the full scope might not be clear initially
- Problems that require a multi-step solution
- Tasks that need to maintain context over multiple steps
- Situations where irrelevant information needs to be filtered out

Key features:
- You can adjust total_thoughts up or down as you progress
- You can question or revise previous thoughts
- You can add more thoughts even after reaching what seemed like the end
- You can express uncertainty and explore alternative approaches
- Not every thought needs to build linearly - you can branch or backtrack
- Generates a solution hypothesis
- Verifies the hypothesis based on the Chain of Thought steps
- Repeats the process until satisfied
- Provides a correct answer

Parameters explained:
- thought: Your current thinking step, which can include:
* Regular analytical steps
* Revisions of previous thoughts
* Questions about previous decisions
* Realizations about needing more analysis
* Changes in approach
* Hypothesis generation
* Hypothesis verification
- next_thought_needed: True if you need more thinking, even if at what seemed like the end
- thought_number: Current number in sequence (can go beyond initial total if needed)
- total_thoughts: Current estimate of thoughts needed (can be adjusted up/down)
- is_revision: A boolean indicating if this thought revises previous thinking
- revises_thought: If is_revision is true, which thought number is being reconsidered
- branch_from_thought: If branching, which thought number is the branching point
- branch_id: Identifier for the current branch (if any)
- needs_more_thoughts: If reaching end but realizing more thoughts needed

You should:
1. Start with an initial estimate of needed thoughts, but be ready to adjust
2. Feel free to question or revise previous thoughts
3. Don't hesitate to add more thoughts if needed, even at the "end"
4. Express uncertainty when present
5. Mark thoughts that revise previous thinking or branch into new paths
6. Ignore information that is irrelevant to the current step
7. Generate a solution hypothesis when appropriate
8. Verify the hypothesis based on the Chain of Thought steps
9. Repeat the process until satisfied with the solution
10. Provide a single, ideally correct answer as the final output
11. Only set next_thought_needed to false when truly done and a satisfactory answer is reached""",
    inputSchema={
        "type": "object",
        "properties": {
            "thought": {"type": "string", "description": "Your current thinking step"},
            "nextThoughtNeeded": {
                "type": "boolean",
                "description": "Whether another thought step is needed",
            },
            "thoughtNumber": {
                "type": "integer",
                "description": "Current thought number",
                "minimum": 1,
            },
            "totalThoughts": {
                "type": "integer",
                "description": "Estimated total thoughts needed",
                "minimum": 1,
            },
            "isRevision": {
                "type": "boolean",
                "description": "Whether this revises previous thinking",
            },
            "revisesThought": {
                "type": "integer",
                "description": "Which thought is being reconsidered",
                "minimum": 1,
            },
            "branchFromThought": {
                "type": "integer",
                "description": "Branching point thought number",
                "minimum": 1,
            },
            "branchId": {"type": "string", "description": "Branch identifier"},
            "needsMoreThoughts": {
                "type": "boolean",
                "description": "If more thoughts are needed",
            },
        },
        "required": ["thought", "nextThoughtNeeded", "thoughtNumber", "totalThoughts"],
    },
)


# Sandboxing is disabled because the MCP library uses anyio/sniffio which requires
# threading capabilities that are restricted in Temporal's workflow sandbox
@workflow.defn(sandboxed=False)
class SequentialThinkingMCPServerWorkflow:
    def __init__(self) -> None:
        self.running = False
        self.thought_history: list[dict[str, Any]] = []
        self.branches: dict[str, list[dict[str, Any]]] = {}

    @workflow.run
    async def start(self):
        self.running = True
        await workflow.wait_condition(lambda: not self.running)

    @workflow.update
    def stop(self):
        self.running = False

    @workflow.query
    def list_tools(self, request: ListToolsRequest) -> ListToolsResult:
        """Handle tools/list request."""
        return ListToolsResult(tools=[SEQUENTIAL_THINKING_TOOL])

    @workflow.update
    async def call_tool(self, request: CallToolRequest) -> CallToolResult:
        """Handle tools/call request."""
        if request.params.name == "sequentialthinking":
            return self.process_thought(request.params.arguments)
        else:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Unknown tool: {request.params.name}",
                    )
                ],
                isError=True,
            )

    def process_thought(self, arguments: dict[str, Any] | None) -> CallToolResult:
        """Process a sequential thinking step."""
        try:
            # Validate input
            validated_input = validate_thought_data(arguments or {})

            # Adjust totalThoughts if thoughtNumber exceeds it
            if validated_input["thoughtNumber"] > validated_input["totalThoughts"]:
                validated_input["totalThoughts"] = validated_input["thoughtNumber"]

            # Add to thought history
            self.thought_history.append(validated_input)

            # Handle branches
            if validated_input.get("branchFromThought") and validated_input.get(
                "branchId"
            ):
                branch_id = validated_input["branchId"]
                if branch_id not in self.branches:
                    self.branches[branch_id] = []
                self.branches[branch_id].append(validated_input)

            # Return metadata about the thought processing
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "thoughtNumber": validated_input["thoughtNumber"],
                                "totalThoughts": validated_input["totalThoughts"],
                                "nextThoughtNeeded": validated_input[
                                    "nextThoughtNeeded"
                                ],
                                "branches": list(self.branches.keys()),
                                "thoughtHistoryLength": len(self.thought_history),
                            },
                            indent=2,
                        ),
                    )
                ],
                isError=False,
            )
        except Exception as e:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {"error": str(e), "status": "failed"}, indent=2
                        ),
                    )
                ],
                isError=True,
            )


def validate_thought_data(data: dict[str, Any]) -> dict[str, Any]:
    """Validate thought data matches expected schema."""
    # Required fields
    if not data.get("thought") or not isinstance(data["thought"], str):
        raise ValueError("Invalid thought: must be a string")

    if not data.get("thoughtNumber") or not isinstance(data["thoughtNumber"], int):
        raise ValueError("Invalid thoughtNumber: must be a number")

    if not data.get("totalThoughts") or not isinstance(data["totalThoughts"], int):
        raise ValueError("Invalid totalThoughts: must be a number")

    if "nextThoughtNeeded" not in data or not isinstance(
        data["nextThoughtNeeded"], bool
    ):
        raise ValueError("Invalid nextThoughtNeeded: must be a boolean")

    # Build validated result with required fields
    result = {
        "thought": data["thought"],
        "thoughtNumber": data["thoughtNumber"],
        "totalThoughts": data["totalThoughts"],
        "nextThoughtNeeded": data["nextThoughtNeeded"],
    }

    # Optional fields
    if "isRevision" in data:
        result["isRevision"] = bool(data["isRevision"])

    if "revisesThought" in data:
        result["revisesThought"] = int(data["revisesThought"])

    if "branchFromThought" in data:
        result["branchFromThought"] = int(data["branchFromThought"])

    if "branchId" in data:
        result["branchId"] = str(data["branchId"])

    if "needsMoreThoughts" in data:
        result["needsMoreThoughts"] = bool(data["needsMoreThoughts"])

    return result
