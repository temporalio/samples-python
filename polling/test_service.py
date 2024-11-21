from dataclasses import dataclass


@dataclass
class ComposeGreetingInput:
    greeting: str
    name: str


try_attempts = 0


class TestService:
    def __init__(self):
        self.error_attempts = 5

    async def get_service_result(self, input):
        global try_attempts
        print(f"Attempt {try_attempts} of {self.error_attempts} to invoke service")
        try_attempts += 1
        if try_attempts % self.error_attempts == 0:
            return f"{input.greeting}, {input.name}!"
        raise Exception("service is down")
