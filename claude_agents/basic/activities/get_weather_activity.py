"""Weather activity for Claude Agent examples."""

from dataclasses import dataclass

from temporalio import activity


@dataclass
class Weather:
    """Weather data for a city."""

    city: str
    temperature_range: str
    conditions: str


@activity.defn
async def get_weather(city: str) -> Weather:
    """Get the weather for a given city.

    This is a mock activity that returns fixed weather data.
    In a real application, this would call a weather API.

    Args:
        city: The city to get weather for

    Returns:
        Weather data for the city
    """
    return Weather(
        city=city,
        temperature_range="14-20C",
        conditions="Sunny with wind."
    )