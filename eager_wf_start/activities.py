from temporalio import activity

@activity.defn()
async def greeting(name: str) -> str:
    return f"Hello {name}!"