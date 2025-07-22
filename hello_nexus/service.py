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


@dataclass
class MyInput:
    name: str


@dataclass
class MyOutput:
    message: str


@nexusrpc.service
class MyNexusService:
    my_sync_operation: nexusrpc.Operation[MyInput, MyOutput]
    my_workflow_run_operation: nexusrpc.Operation[MyInput, MyOutput]
