from temporalio import activity


@activity.defn
async def greet(inp: str) -> str:
    return f"Hi from {inp}"


@activity.defn
async def super_greet(inp: str, some_number: int) -> str:
    return f"Hi from {inp} with {some_number}"
