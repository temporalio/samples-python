import asyncio

from temporalio import common, exceptions, workflow

from dan.utils.client import start_workflow


@workflow.defn
class Workflow:
    @workflow.run
    async def run(self) -> str:
        attempts = 6
        res1 = await workflow.execute_child_workflow(
            ChildWorkflow.run,
            "a",
            retry_policy=common.RetryPolicy(maximum_attempts=attempts),
        )
        res2 = await workflow.execute_child_workflow(
            ChildWorkflow.run,
            "b",
            retry_policy=common.RetryPolicy(maximum_attempts=attempts),
        )
        return f"workflow-result--{res1}--{res2}"


attempt = 0


@workflow.defn
class ChildWorkflow:
    @workflow.run
    async def run(self, arg: str) -> str:
        global attempt
        attempt += 1
        if attempt < 5:
            raise exceptions.Act("deliberate")
        return f"child-workflow-result-{arg}"


workflows = [Workflow, ChildWorkflow]


async def main():
    wf_handle = await start_workflow(Workflow.run)
    print("workflow handle:", wf_handle)
    print("workflow result:", await wf_handle.result())


if __name__ == "__main__":
    asyncio.run(main())
