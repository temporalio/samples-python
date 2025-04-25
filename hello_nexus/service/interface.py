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


# TODO(dan): for now, making interface explicit in imports to distinguish from handler
# implementation. Final import scheme and names TBD.
@nexusrpc.interface.service
class MyNexusService:
    echo: nexusrpc.interface.Operation[EchoInput, EchoOutput]
    hello: nexusrpc.interface.Operation[HelloInput, HelloOutput]
    echo2: nexusrpc.interface.Operation[EchoInput, EchoOutput]
    hello2: nexusrpc.interface.Operation[HelloInput, HelloOutput]
    echo3: nexusrpc.interface.Operation[EchoInput, EchoOutput]
    hello3: nexusrpc.interface.Operation[HelloInput, HelloOutput]
