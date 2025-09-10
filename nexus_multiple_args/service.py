"""
This is a Nexus service definition that demonstrates multiple argument handling.

A service definition defines a Nexus service as a named collection of operations, each
with input and output types. It does not implement operation handling: see the service
handler and operation handlers in nexus_multiple_args.handler.service_handler for that.

A Nexus service definition is used by Nexus callers (e.g. a Temporal workflow) to create
type-safe clients, and it is used by Nexus handlers to validate that they implement
correctly-named operation handlers with the correct input and output types.

The service defined in this file features one operation: hello, where hello
demonstrates handling multiple arguments through a single input object.
"""

from dataclasses import dataclass
from enum import StrEnum

import nexusrpc


class Language(StrEnum):
    EN = "EN"
    FR = "FR"
    DE = "DE"
    ES = "ES"
    TR = "TR"


@dataclass
class HelloInput:
    name: str
    language: Language


@dataclass
class HelloOutput:
    message: str


@nexusrpc.service
class MyNexusService:
    hello: nexusrpc.Operation[HelloInput, HelloOutput]
