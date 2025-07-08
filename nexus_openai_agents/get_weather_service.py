"""
This is a Nexus service definition.

A service definition defines a Nexus service as a named collection of operations, each
with input and output types. It does not implement operation handling: see the service
handler and operation handlers in hello_nexus.handler.nexus_service for that.

A Nexus service definition is used by Nexus callers (e.g. a Temporal workflow) to create
type-safe clients, and it is used by Nexus handlers to validate that they implement
correctly-named operation handlers with the correct input and output types.

The service defined in this file features two operations: echo and hello.
"""

from dataclasses import dataclass

import nexusrpc
from nexus_openai_agents.get_weather_workflow import Weather


@dataclass
class GetWeatherInput:
    city: str


@nexusrpc.service
class GetWeatherService:
    get_weather: nexusrpc.Operation[GetWeatherInput, Weather]
