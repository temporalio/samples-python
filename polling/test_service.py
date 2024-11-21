class TestService:
    def __init__(self, error_attempts: int = 5):
        self.try_attempts = 0
        self.error_attempts = error_attempts

    async def get_service_result(self, input):
        print(
            f"Attempt {self.try_attempts}"
            f" of {self.error_attempts} to invoke service"
        )
        self.try_attempts += 1
        if self.try_attempts % self.error_attempts == 0:
            return f"{input.greeting}, {input.name}!"
        raise Exception("service is down")
