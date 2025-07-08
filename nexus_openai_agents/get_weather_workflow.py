from dataclasses import dataclass

from temporalio import workflow


@dataclass
class Weather:
    city: str
    temperature_range: str
    conditions: str


@workflow.defn
class GetWeatherWorkflow:
    @workflow.run
    async def run(self, city: str) -> Weather:
        """
        Workflow to get the weather for a given city.
        """
        return Weather(city=city, temperature_range="14-20C", conditions="Sunny with wind.")
