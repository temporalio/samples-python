"""Nexus service definition shared by the caller and handler."""

from dataclasses import dataclass

import nexusrpc


@dataclass
class GreetingInput:
    name: str


@dataclass
class GreetingOutput:
    message: str


@nexusrpc.service
class GreetingService:
    greet: nexusrpc.Operation[GreetingInput, GreetingOutput]
