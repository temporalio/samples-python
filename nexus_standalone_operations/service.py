"""Nexus service definition for standalone operations sample.

Defines a Nexus service with two operations:
- echo: a synchronous operation that echoes the input message
- hello: an asynchronous (workflow-backed) operation that returns a greeting

This service definition is used by both the handler (to validate operation
signatures) and the client (to create type-safe nexus clients).
"""

from dataclasses import dataclass

import nexusrpc


@dataclass
class EchoInput:
    message: str


@dataclass
class EchoOutput:
    message: str


@dataclass
class HelloInput:
    name: str


@dataclass
class HelloOutput:
    greeting: str


@nexusrpc.service
class MyNexusService:
    echo: nexusrpc.Operation[EchoInput, EchoOutput]
    hello: nexusrpc.Operation[HelloInput, HelloOutput]
