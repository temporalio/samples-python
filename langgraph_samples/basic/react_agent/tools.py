"""Tool definitions for the ReAct Agent.

These tools demonstrate how to wrap LangChain tools for durable execution
using temporal_tool().
"""

from langchain_core.tools import tool


@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city.

    Args:
        city: The city name to get weather for.

    Returns:
        A string describing the current weather conditions.
    """
    # Simulated weather data - in production, call a real weather API
    weather_data = {
        "new york": "72°F, Partly cloudy with light winds",
        "london": "58°F, Overcast with chance of rain",
        "tokyo": "68°F, Clear skies",
        "paris": "65°F, Sunny with occasional clouds",
        "sydney": "77°F, Warm and humid",
    }
    city_lower = city.lower()
    return weather_data.get(city_lower, f"Weather data not available for {city}")


@tool
def calculate(expression: str) -> str:
    """Perform a mathematical calculation.

    Args:
        expression: A mathematical expression like "2 + 2" or "10 * 5".

    Returns:
        The result of the calculation as a string.
    """
    try:
        # Safely evaluate mathematical expressions
        # Only allow basic math operations
        allowed_chars = set("0123456789+-*/(). ")
        if not all(c in allowed_chars for c in expression):
            return "Error: Only basic math operations are allowed"
        result = eval(expression)  # noqa: S307
        return str(result)
    except Exception as e:
        return f"Error calculating: {e}"


@tool
def search_knowledge(query: str) -> str:
    """Search a knowledge base for information.

    Args:
        query: The search query.

    Returns:
        Relevant information from the knowledge base.
    """
    # Simulated knowledge base - in production, use a real search/RAG system
    knowledge = {
        "temporal": "Temporal is a durable execution platform that helps developers build reliable applications. It provides fault tolerance, state management, and workflow orchestration.",
        "langgraph": "LangGraph is a library for building stateful, multi-actor applications with LLMs. It enables creating agent workflows with cycles, conditionals, and state management.",
        "react": "ReAct (Reasoning + Acting) is an agent pattern where the AI alternates between thinking about what to do and taking actions. It improves reliability by making the reasoning process explicit.",
        "python": "Python is a high-level programming language known for its readability and versatility. It's widely used in AI/ML, web development, and automation.",
    }
    query_lower = query.lower()
    for key, value in knowledge.items():
        if key in query_lower:
            return value
    return f"No specific information found for '{query}'. Try searching for: temporal, langgraph, react, or python."
