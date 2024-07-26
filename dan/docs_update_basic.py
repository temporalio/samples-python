import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import temporalio.client
import temporalio.service
from temporalio import common, workflow
from temporalio.client import Client
from temporalio.exceptions import ApplicationError
from temporalio.worker import Worker

wid = __file__
tq = "tq"


class ShouldExit(Enum):
    Yes = 1
    NotYet = 2
    Fail = 3


@dataclass
class HelloWorldInput:
    entity_to_be_greeted: str


@workflow.defn
class HelloWorldWorkflow:
    def __init__(self):
        self.entity_to_be_greeted: Optional[str] = None
        self.should_exit: ShouldExit = ShouldExit.NotYet

    @workflow.run
    async def run(self) -> str:
        await workflow.wait_condition(lambda: self.should_exit != ShouldExit.NotYet)
        if self.should_exit is ShouldExit.Fail:
            raise ApplicationError("Workflow author deliberately failed the Workflow")
        return self.greeting()

    @workflow.update
    async def set_greeting(self, input: HelloWorldInput) -> str:
        self.entity_to_be_greeted = input.entity_to_be_greeted
        if input.entity_to_be_greeted == "<fail-update>":
            raise ApplicationError(
                "Workflow author deliberately failed the Update (but not the Workflow)"
            )
        elif input.entity_to_be_greeted == "<fail-workflow>":
            self.should_exit = ShouldExit.Fail
            await workflow.wait_condition(lambda: False)
            return "unreachable"
        else:
            return self.greeting()

    @set_greeting.validator
    def set_greeting_validator(self, input: HelloWorldInput) -> None:
        if input.entity_to_be_greeted not in {
            "world",
            "World",
            "<fail-update>",
            "<fail-workflow>",
        }:
            raise Exception(f"invalid entity: {input.entity_to_be_greeted}")

    @workflow.signal
    def exit(self) -> None:
        self.should_exit = ShouldExit.Yes

    def greeting(self) -> str:
        return f"Hello, {self.entity_to_be_greeted}!"


async def main():
    client = await Client.connect("localhost:7233")
    async with Worker(
        client,
        task_queue=tq,
        workflows=[HelloWorldWorkflow],
    ):
        handle = await client.start_workflow(
            HelloWorldWorkflow.run,
            id=wid,
            task_queue=tq,
            id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
        )

        # execute_update: success
        update_result = await handle.execute_update(
            HelloWorldWorkflow.set_greeting,
            HelloWorldInput("world"),
        )
        print(f"execute_update: result: {update_result}")

        # execute_update: rejected
        try:
            update_result = await handle.execute_update(
                HelloWorldWorkflow.set_greeting,
                HelloWorldInput("mars"),
            )
        except temporalio.client.WorkflowUpdateFailedError as err:
            print(f"execute_update: update rejected: {err.__class__}({err})")

        # execute_update: fail update
        try:
            update_result = await handle.execute_update(
                HelloWorldWorkflow.set_greeting,
                HelloWorldInput("<fail-update>"),
            )
        except temporalio.client.WorkflowUpdateFailedError as err:
            print(f"execute_update: update failed: {err.__class__}({err})")

        # start_update: success
        update_handle = await handle.start_update(
            HelloWorldWorkflow.set_greeting,
            HelloWorldInput("World"),
        )
        update_result = await update_handle.result()
        print(f"handle.result(): {update_result}")

        # start_update: rejected
        try:
            update_handle = await handle.start_update(
                HelloWorldWorkflow.set_greeting,
                HelloWorldInput("mars"),
            )
        except temporalio.client.WorkflowUpdateFailedError as err:
            print(f"start_update: rejected: {err.__class__}({err})")

        # start_update: failed
        try:
            update_handle = await handle.start_update(
                HelloWorldWorkflow.set_greeting,
                HelloWorldInput("<fail-update>"),
            )
        except temporalio.client.WorkflowUpdateFailedError as err:
            print(f"start_update: failed: {err.__class__}({err})")

        #
        # Workflow exit
        #

        # execute_update: fail workflow
        try:
            update_result = await handle.execute_update(
                HelloWorldWorkflow.set_greeting,
                HelloWorldInput("<fail-workflow>"),
            )
        except Exception as err:
            print(f"execute_update: workflow failed: {err.__class__}({err})")

        print("waiting for workflow to end...")
        # result = await handle.result()
        # print(f"Workflow Result: {result}")

        # execute_update: workflow doesn't exist
        try:
            update_result = await handle.execute_update(
                HelloWorldWorkflow.set_greeting,
                HelloWorldInput(""),
            )
        except temporalio.service.RPCError as err:
            # The update was rejected
            print(f"execute_update: workflow doesn't exist: {err.__class__}({err})")

        # start_update: workflow doesn't exist
        try:
            update_handle = await handle.start_update(
                HelloWorldWorkflow.set_greeting,
                HelloWorldInput(""),
            )
        except temporalio.service.RPCError as err:
            # The update was rejected
            print(f"start_update: workflow doesn't exist: {err.__class__}({err})")


if __name__ == "__main__":
    asyncio.run(main())
