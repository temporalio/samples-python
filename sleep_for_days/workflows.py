import asyncio
from datetime import timedelta
from temporalio import workflow
from dataclasses import dataclass
from sleep_for_days.activities import send_email, SendEmailInput

@dataclass
class SleepForDaysInput:
    numOfDays: int

@workflow.defn(name="SleepForDaysWorkflow")
class SleepForDaysWorkflow:

    def __init__(self) -> None:
        self.is_complete = False

    @workflow.run
    async def run(self, input: SleepForDaysInput) -> str:
        while(not self.is_complete):
            await workflow.execute_activity(send_email, SendEmailInput(f"{input.numOfDays} until the next email"), start_to_close_timeout=timedelta(seconds=10))
            await workflow.wait([
                asyncio.create_task(workflow.sleep(input.numOfDays * 24 * 60 * 60)),
                asyncio.create_task(workflow.wait_condition(lambda: self.is_complete))
            ], return_when=asyncio.FIRST_COMPLETED)
        return "done!"
    
    @workflow.signal
    def complete(self):
        self.is_complete = True