from dataclasses import dataclass

from openai import BaseModel
from temporalio import activity


class Weather(BaseModel):
    city: str
    temperature_range: str
    conditions: str


@dataclass
class Weather:
    city: str
    temperature_range: str
    conditions: str


@activity.defn
async def get_weather(city: str) -> Weather:
    """
    Get the weather for a given city.
    """
    return Weather(city=city, temperature_range="14-20C", conditions="Sunny with wind.")
