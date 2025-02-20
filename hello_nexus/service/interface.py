from dataclasses import dataclass

import nexusrpc


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


@nexusrpc.service
class MyNexusService:
    echo: nexusrpc.Operation[EchoInput, EchoOutput]
    hello: nexusrpc.Operation[HelloInput, HelloOutput]
    echo2: nexusrpc.Operation[EchoInput, EchoOutput]
    hello2: nexusrpc.Operation[HelloInput, HelloOutput]
    echo3: nexusrpc.Operation[EchoInput, EchoOutput]
    hello3: nexusrpc.Operation[HelloInput, HelloOutput]
