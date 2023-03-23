from temporalio import activity

from your_dataobject import YourParams


@activity.defn
async def your_activity(input: YourParams) -> str:
    return f"{input.greeting}, {input.name}!"
