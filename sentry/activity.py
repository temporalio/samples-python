from dataclasses import dataclass

from temporalio import activity


@dataclass
class WorkingActivityInput:
    message: str


@activity.defn
async def working_activity(input: WorkingActivityInput) -> str:
    activity.logger.info("Running activity with parameter %s" % input)
    return "Success"


@dataclass
class BrokenActivityInput:
    message: str


@activity.defn
async def broken_activity(input: BrokenActivityInput) -> str:
    activity.logger.info("Running activity with parameter %s" % input)
    raise Exception("Activity failed!")
