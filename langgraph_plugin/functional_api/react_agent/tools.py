"""Tool definitions for the ReAct Agent.

These are standard LangChain tools that will be called from @task functions.
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
