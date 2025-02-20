from dataclasses import dataclass

from nexusrpc.interface import NexusOperation, nexus_service


@dataclass
class HelloInput:
    name: str


@dataclass
class HelloOutput:
    message: str


@dataclass
class EchoInput:
    message: str


@dataclass
class EchoOutput:
    message: str


@nexus_service
class MyNexusService:
    echo: NexusOperation[EchoInput, EchoOutput]
    echo2: NexusOperation[EchoInput, EchoOutput]
    echo3: NexusOperation[EchoInput, EchoOutput]
    hello: NexusOperation[HelloInput, HelloOutput]
    hello2: NexusOperation[HelloInput, HelloOutput]
    hello3: NexusOperation[HelloInput, HelloOutput]
