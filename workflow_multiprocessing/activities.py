import os
from temporalio import activity


@activity.defn
async def echo_pid_activity(input: str) -> str:
    return f"{input} | activity-pid:{os.getpid()}"
