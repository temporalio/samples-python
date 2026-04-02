"""Task definitions for the ReAct Agent.

Each @task function runs as a Temporal activity, providing automatic retries
and failure recovery for LLM calls and tool executions.
"""

import os
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.func import task

from langgraph_plugin.functional_api.react_agent.tools import calculate, get_weather


@task
async def call_model(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Call the LLM to decide what action to take.

    This task runs as a Temporal activity, so LLM failures are automatically retried.

    Args:
        messages: The conversation history as a list of message dicts.

    Returns:
        Dict containing the AI message response with potential tool calls.
    """
    model = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
    )

    # Bind tools to the model
    tools = [get_weather, calculate]
    model_with_tools = model.bind_tools(tools)

    # Convert dict messages to LangChain message objects
    lc_messages: list[BaseMessage] = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            lc_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            tool_calls = msg.get("tool_calls")
            if tool_calls:
                lc_messages.append(AIMessage(content=content, tool_calls=tool_calls))
            else:
                lc_messages.append(AIMessage(content=content))
        elif role == "tool":
            lc_messages.append(
                ToolMessage(
                    content=content,
                    tool_call_id=msg.get("tool_call_id", ""),
                )
            )

    # Call the model
    response = await model_with_tools.ainvoke(lc_messages)

    # Convert response to serializable dict
    result: dict[str, Any] = {
        "role": "assistant",
        "content": response.content,
    }

    if hasattr(response, "tool_calls") and response.tool_calls:
        result["tool_calls"] = [
            {
                "id": tc["id"],
                "name": tc["name"],
                "args": tc["args"],
            }
            for tc in response.tool_calls
        ]

    return result


@task
async def execute_tools(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Execute the requested tools and return results.

    This task runs as a Temporal activity, so tool executions are automatically retried.

    Args:
        tool_calls: List of tool calls from the model response.

    Returns:
        List of tool result message dicts.
    """
    tools_by_name = {
        "get_weather": get_weather,
        "calculate": calculate,
    }

    results = []
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_id = tool_call["id"]

        tool_fn = tools_by_name.get(tool_name)
        if tool_fn:
            try:
                result = tool_fn.invoke(tool_args)
            except Exception as e:
                result = f"Error executing {tool_name}: {e}"
        else:
            result = f"Unknown tool: {tool_name}"

        results.append(
            {
                "role": "tool",
                "content": str(result),
                "tool_call_id": tool_id,
            }
        )

    return results
