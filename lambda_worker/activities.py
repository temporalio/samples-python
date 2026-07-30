from temporalio import activity


@activity.defn
async def hello_activity(name: str) -> str:
    activity.logger.info("HelloActivity started with name: %s", name)
    return f"Hello, {name}!"
