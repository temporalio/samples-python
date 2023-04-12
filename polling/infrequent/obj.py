from dataclasses import dataclass


@dataclass
class ComposeGreetingInput:
    greeting: str
    name: str
