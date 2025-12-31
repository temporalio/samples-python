"""Plan-and-Execute Agent Graph Definition.

This module implements a plan-and-execute agent that first creates a plan,
then executes each step sequentially with the ability to replan based on results.

The agent pattern separates planning from execution:
1. Planner creates a high-level plan with specific steps
2. Executor runs each step using available tools
3. After each step, the agent can replan if needed
4. Progress is tracked and visible through Temporal

Flow:
1. plan - Create initial plan from the objective
2. execute_step - Run the next step using tools
3. evaluate - Check if more steps needed or replanning required
4. replan (optional) - Adjust remaining steps based on results
5. respond - Generate final response when complete

Note: This module is only imported by the worker (not by the workflow).
LangGraph cannot be imported in the workflow sandbox.
"""

import os
from typing import Annotated, Any, Literal

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from langchain.agents import create_agent


class PlanStep(BaseModel):
    """A single step in the execution plan."""

    step_number: int = Field(description="The step number (1-indexed)")
    description: str = Field(description="What this step should accomplish")
    tool_hint: str = Field(
        description="Suggested tool to use (calculate, lookup, or analyze)"
    )


class Plan(BaseModel):
    """An execution plan with ordered steps."""

    objective: str = Field(description="The main objective to accomplish")
    steps: list[PlanStep] = Field(
        description="Ordered list of steps to execute", min_length=1, max_length=5
    )


class StepResult(BaseModel):
    """Result of executing a single step."""

    step_number: int
    description: str
    result: str
    success: bool


class PlanExecuteState(TypedDict):
    """State for the plan-and-execute graph.

    Attributes:
        messages: Conversation history with messages.
        objective: The main task objective.
        plan: The current execution plan.
        step_results: Results from completed steps.
        current_step: Index of the current step (0-indexed).
        needs_replan: Whether replanning is needed.
    """

    messages: Annotated[list[BaseMessage], add_messages]
    objective: str
    plan: Plan | None
    step_results: list[StepResult]
    current_step: int
    needs_replan: bool


# Helper functions to handle dict/object access after Temporal serialization
def _get_plan_steps(plan: Plan | dict[str, Any]) -> list[Any]:
    """Get steps from Plan, handling both object and dict forms."""
    if isinstance(plan, dict):
        return plan.get("steps", [])
    return list(plan.steps)


def _get_step_attr(
    step: PlanStep | dict[str, Any], attr: str, default: Any = ""
) -> Any:
    """Get attribute from PlanStep, handling both object and dict forms."""
    if isinstance(step, dict):
        return step.get(attr, default)
    return getattr(step, attr, default)


def _get_result_success(result: StepResult | dict[str, Any]) -> bool:
    """Get success from StepResult, handling both object and dict forms."""
    if isinstance(result, dict):
        return result.get("success", False)
    return result.success


# Define tools for the executor agent
@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression.

    Args:
        expression: A mathematical expression like "2 + 2" or "10 * 5"

    Returns:
        The result of the calculation
    """
    try:
        # Safe evaluation of mathematical expressions
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            return "Error: Invalid characters in expression"
        result = eval(expression)  # noqa: S307
        return f"Result: {result}"
    except Exception as e:
        return f"Error calculating: {str(e)}"


@tool
def lookup(topic: str) -> str:
    """Look up information about a topic.

    Args:
        topic: The topic to look up information about

    Returns:
        Information about the topic
    """
    # Mock knowledge base
    knowledge = {
        "python": "Python is a high-level programming language known for its simplicity and readability.",
        "temporal": "Temporal is a durable execution platform for running reliable workflows.",
        "langgraph": "LangGraph is a library for building stateful, multi-actor LLM applications.",
        "agents": "AI agents are autonomous systems that use LLMs to make decisions and take actions.",
        "planning": "Planning agents first create a plan, then execute steps sequentially.",
    }

    topic_lower = topic.lower()
    for key, value in knowledge.items():
        if key in topic_lower:
            return value

    return f"No specific information found about '{topic}'. Consider breaking down the query."


@tool
def analyze(data: str) -> str:
    """Analyze data or text and provide insights.

    Args:
        data: The data or text to analyze

    Returns:
        Analysis results
    """
    # Simple mock analysis
    word_count = len(data.split())
    char_count = len(data)
    return f"Analysis: {word_count} words, {char_count} characters. The content discusses: {data[:100]}..."


def build_plan_and_execute_graph() -> Any:
    """Build a plan-and-execute agent graph.

    The graph implements a planning workflow that:
    1. Creates a plan with specific steps
    2. Executes each step using available tools
    3. Evaluates progress and replans if needed
    4. Generates a final response

    Returns:
        A compiled LangGraph that can be executed with ainvoke().
    """
    model = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
    )

    # Build executor agent with tools
    tools = [calculate, lookup, analyze]
    executor_agent: Any = create_agent(model, tools)

    def create_plan(state: PlanExecuteState) -> dict[str, Any]:
        """Create an execution plan from the objective.

        Analyzes the objective and breaks it down into
        specific, actionable steps.
        """
        messages = state["messages"]
        objective = next(
            (m.content for m in messages if isinstance(m, HumanMessage)),
            "Complete the task",
        )

        plan_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a planning agent. Given an objective, create a step-by-step
plan to accomplish it. Each step should be specific and actionable.

Available tools for execution:
- calculate: For mathematical computations
- lookup: For retrieving information about topics
- analyze: For analyzing data or text

Create 2-4 steps that can be executed sequentially.""",
                ),
                ("human", "Objective: {objective}"),
            ]
        )

        planner = plan_prompt | model.with_structured_output(Plan)
        plan = planner.invoke({"objective": str(objective)})

        return {
            "objective": str(objective),
            "plan": plan,
            "current_step": 0,
            "step_results": [],
            "needs_replan": False,
        }

    def execute_step(state: PlanExecuteState) -> dict[str, Any]:
        """Execute the current step using the executor agent.

        Runs the executor agent with the step description as input.
        The agent uses available tools to complete the step.
        """
        plan = state.get("plan")
        current_step = state.get("current_step", 0)

        steps = _get_plan_steps(plan) if plan else []
        if not plan or current_step >= len(steps):
            return {"needs_replan": False}

        step = steps[current_step]
        step_number = _get_step_attr(step, "step_number", 0)
        step_desc = _get_step_attr(step, "description", "")
        tool_hint = _get_step_attr(step, "tool_hint", "")

        # Run the executor agent for this step
        result = executor_agent.invoke(
            {
                "messages": [
                    SystemMessage(
                        content=f"You are executing step {step_number} of a plan. "
                        f"Complete this step: {step_desc}\n"
                        f"Suggested tool: {tool_hint}"
                    ),
                    HumanMessage(content=step_desc),
                ]
            }
        )

        # Extract the result from the agent's response
        result_content = ""
        if result.get("messages"):
            last_msg = result["messages"][-1]
            result_content = (
                last_msg.content if hasattr(last_msg, "content") else str(last_msg)
            )

        step_result = StepResult(
            step_number=step_number,
            description=step_desc,
            result=result_content,
            success=True,
        )

        return {
            "step_results": state.get("step_results", []) + [step_result],
            "current_step": current_step + 1,
            "messages": [
                {
                    "role": "assistant",
                    "content": f"Step {step_number} completed: {result_content[:200]}...",
                }
            ],
        }

    def evaluate_progress(state: PlanExecuteState) -> dict[str, Any]:
        """Evaluate if we should continue, replan, or finish.

        Checks completion status and determines next action.
        """
        plan = state.get("plan")
        current_step = state.get("current_step", 0)
        step_results = state.get("step_results", [])

        if not plan:
            return {"needs_replan": True}

        # Check if all steps completed
        steps = _get_plan_steps(plan)
        all_complete = current_step >= len(steps)

        # Check if any step failed
        failed_steps = [r for r in step_results if not _get_result_success(r)]

        return {
            "needs_replan": len(failed_steps) > 0,
            "messages": [
                {
                    "role": "assistant",
                    "content": f"Progress: {current_step}/{len(steps)} steps complete. "
                    f"Failures: {len(failed_steps)}",
                }
            ]
            if not all_complete
            else [],
        }

    def should_continue(
        state: PlanExecuteState,
    ) -> Literal["execute", "replan", "respond"]:
        """Decide whether to continue execution, replan, or respond.

        Routes based on:
        - needs_replan flag -> replan
        - more steps remaining -> execute
        - all steps complete -> respond
        """
        if state.get("needs_replan", False):
            return "replan"

        plan = state.get("plan")
        current_step = state.get("current_step", 0)

        if plan and current_step < len(_get_plan_steps(plan)):
            return "execute"

        return "respond"

    def replan(state: PlanExecuteState) -> dict[str, Any]:
        """Adjust the plan based on execution results.

        Creates a new plan considering what has been accomplished
        and what failed, to better achieve the objective.
        """
        objective = state.get("objective", "Complete the task")
        step_results = state.get("step_results", [])

        # Format completed work
        completed = "\n".join(
            f"- Step {r.step_number}: {r.description} -> {r.result[:100]}"
            for r in step_results
        )

        replan_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a replanning agent. Given the original objective and
work completed so far, create a new plan for remaining work.

Available tools: calculate, lookup, analyze

Consider what has already been accomplished and create 1-3 new steps
to complete the objective.""",
                ),
                (
                    "human",
                    "Objective: {objective}\n\nCompleted work:\n{completed}\n\nCreate new plan:",
                ),
            ]
        )

        planner = replan_prompt | model.with_structured_output(Plan)
        new_plan = planner.invoke({"objective": objective, "completed": completed})

        return {
            "plan": new_plan,
            "current_step": 0,
            "needs_replan": False,
        }

    def respond(state: PlanExecuteState) -> dict[str, Any]:
        """Generate the final response summarizing the execution.

        Compiles all step results into a coherent final answer.
        """
        objective = state.get("objective", "")
        step_results = state.get("step_results", [])

        # Format all results
        results_text = "\n".join(
            f"{r.step_number}. {r.description}: {r.result}" for r in step_results
        )

        response_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a summarizer. Given an objective and the results of
executing a plan, provide a clear, concise final answer.

Focus on directly answering the original objective using the
gathered information.""",
                ),
                (
                    "human",
                    "Objective: {objective}\n\nExecution results:\n{results}\n\nProvide final answer:",
                ),
            ]
        )

        chain = response_prompt | model | StrOutputParser()
        response = chain.invoke({"objective": objective, "results": results_text})

        return {"messages": [{"role": "assistant", "content": response}]}

    # Build the plan-and-execute graph
    workflow = StateGraph(PlanExecuteState)

    # Add nodes
    workflow.add_node("plan", create_plan)
    workflow.add_node("execute", execute_step)
    workflow.add_node("evaluate", evaluate_progress)
    workflow.add_node("replan", replan)
    workflow.add_node("respond", respond)

    # Add edges
    workflow.add_edge(START, "plan")
    workflow.add_edge("plan", "execute")
    workflow.add_edge("execute", "evaluate")

    # Conditional routing after evaluation
    workflow.add_conditional_edges(
        "evaluate",
        should_continue,
        {"execute": "execute", "replan": "replan", "respond": "respond"},
    )

    # After replanning, continue execution
    workflow.add_edge("replan", "execute")

    workflow.add_edge("respond", END)

    return workflow.compile()
