import asyncio
import logging
import pprint

from temporalio import workflow
from temporalio.client import WorkflowUpdateStage

from dan.utils import start_workflow


class CustomFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord):
        return pprint.pformat(record.__dict__)


formatter = CustomFormatter()
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.INFO)


@workflow.defn
class Workflow:
    def __init__(self):
        self.is_complete = False

    @workflow.run
    async def run(self) -> None:
        workflow.logger.info("logging: run()")
        print("printed: in run")
        await workflow.wait_condition(lambda: self.is_complete)

    @workflow.update
    async def my_update(self) -> None:
        workflow.logger.info(
            "logging: my_update()", extra={"my-extra-key": "my-extra-val"}
        )
        print("printed: my_update")
        self.is_complete = True


async def main():
    handle = await start_workflow(Workflow.run)
    update_handle = await handle.start_update(
        Workflow.my_update, wait_for_stage=WorkflowUpdateStage.ACCEPTED
    )
    await update_handle.result()
    await handle.result()


if __name__ == "__main__":
    asyncio.run(main())
