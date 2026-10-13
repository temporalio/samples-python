from temporalio import activity


@activity.defn
async def uppercase(input: str) -> str:
    return input.upper()
