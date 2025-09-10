from __future__ import annotations

import uuid

import nexusrpc
from temporalio import nexus

from nexus_multiple_args.handler.workflows import HelloHandlerWorkflow
from nexus_multiple_args.service import HelloInput, HelloOutput, MyNexusService


# @@@SNIPSTART samples-python-nexus-handler-multiargs
@nexusrpc.handler.service_handler(service=MyNexusService)
class MyNexusServiceHandler:
    """
    Service handler that demonstrates multiple argument handling in Nexus operations.
    """

    # This is a nexus operation that is backed by a Temporal workflow.
    # The key feature here is that it demonstrates how to map a single input object
    # (HelloInput) to a workflow that takes multiple individual arguments.
    @nexus.workflow_run_operation
    async def hello(
        self, ctx: nexus.WorkflowRunOperationContext, input: HelloInput
    ) -> nexus.WorkflowHandle[HelloOutput]:
        """
        Start a workflow with multiple arguments unpacked from the input object.
        """
        return await ctx.start_workflow(
            HelloHandlerWorkflow.run,
            args=[
                input.name,  # First argument: name
                input.language,  # Second argument: language
            ],
            id=str(uuid.uuid4()),
        )


# @@@SNIPEND
