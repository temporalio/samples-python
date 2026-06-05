from temporalio import activity


@activity.defn
async def get_weather(city: str) -> str:
    """Get current weather for a city (mock implementation)."""
    return f"72°F and sunny in {city}"
