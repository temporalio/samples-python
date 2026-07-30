"""
Nexus service definition for the cancellation sample.

Defines a NexusService with a single `hello` operation that takes a name and
language, and returns a greeting message.
"""

from dataclasses import dataclass
from enum import IntEnum

import nexusrpc


class Language(IntEnum):
    EN = 0
    FR = 1
    DE = 2
    ES = 3
    TR = 4


@dataclass
class HelloInput:
    name: str
    language: Language


@dataclass
class HelloOutput:
    message: str


@nexusrpc.service
class NexusService:
    hello: nexusrpc.Operation[HelloInput, HelloOutput]
