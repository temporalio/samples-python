from temporalio import activity


# @@@SNIPSTART google-adk-agents-tools-get-weather
@activity.defn
async def get_weather(city: str) -> str:
    """Return the weather for a city.

    In a real sample this would call a weather API. Here it returns a fixed
    response so the sample runs without external credentials.
    """
    return f"The weather in {city} is warm and sunny, 17 degrees."


# @@@SNIPEND
