class TestService:
    def __init__(self):
        self.error_attempts = 5

    async def get_service_result(self, input, attempt: int):
        print(f"Attempt {attempt} of {self.error_attempts} to invoke service")
        if attempt > self.error_attempts:
            return f"{input.greeting}, {input.name}!"
        raise Exception("service is down")
