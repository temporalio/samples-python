import asyncio
from temporalio import activity
from temporalio.exceptions import ApplicationError, ApplicationErrorCategory

@activity.defn
async def greeting_activities(use_benign: bool) -> None:

    #BENIGN category errors emit DEBUG level logs and do not record metrics
    if use_benign:
        raise ApplicationError(
            message="With benign flag : Greeting not sent",
            category=ApplicationErrorCategory.BENIGN,
        )
    else:
        raise ApplicationError("Without benign flag : Greeting not sent")
