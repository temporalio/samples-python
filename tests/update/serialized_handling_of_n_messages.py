import asyncio
import logging
import uuid
from dataclasses import dataclass
from unittest.mock import patch

import temporalio.api.common.v1
import temporalio.api.enums.v1
import temporalio.api.update.v1
import temporalio.api.workflowservice.v1
from temporalio.client import Client, WorkflowHandle
from temporalio.worker import Worker
from temporalio.workflow import UpdateMethodMultiParam

from update.serialized_handling_of_n_messages import (
    MessageProcessor,
    Result,
    get_current_time,
)


async def test_continue_as_new_doesnt_lose_updates(client: Client):
    with patch(
        "temporalio.workflow.Info.is_continue_as_new_suggested", return_value=True
    ):
        tq = str(uuid.uuid4())
        wf = await client.start_workflow(
            MessageProcessor.run, id=str(uuid.uuid4()), task_queue=tq
        )
        update_requests = [
            UpdateRequest(wf, MessageProcessor.process_message, i) for i in range(10)
        ]
        for req in update_requests:
            await req.wait_until_admitted()

        async with Worker(
            client,
            task_queue=tq,
            workflows=[MessageProcessor],
            activities=[get_current_time],
        ):
            for req in update_requests:
                update_result = await req.task
                assert update_result.startswith(req.expected_result_prefix())


@dataclass
class UpdateRequest:
    wf_handle: WorkflowHandle
    update: UpdateMethodMultiParam
    sequence_number: int

    def __post_init__(self):
        self.task = asyncio.Task[Result](
            self.wf_handle.execute_update(self.update, args=[self.arg], id=self.id)
        )

    async def wait_until_admitted(self):
        while True:
            try:
                return await self._poll_update_non_blocking()
            except Exception as err:
                logging.warning(err)

    async def _poll_update_non_blocking(self):
        req = temporalio.api.workflowservice.v1.PollWorkflowExecutionUpdateRequest(
            namespace=self.wf_handle._client.namespace,
            update_ref=temporalio.api.update.v1.UpdateRef(
                workflow_execution=temporalio.api.common.v1.WorkflowExecution(
                    workflow_id=self.wf_handle.id,
                    run_id="",
                ),
                update_id=self.id,
            ),
            identity=self.wf_handle._client.identity,
        )
        res = await self.wf_handle._client.workflow_service.poll_workflow_execution_update(
            req
        )
        # TODO: @cretz how do we work with these raw proto objects?
        assert "stage: UPDATE_WORKFLOW_EXECUTION_LIFECYCLE_STAGE_ADMITTED" in str(res)

    @property
    def arg(self) -> str:
        return str(self.sequence_number)

    @property
    def id(self) -> str:
        return str(self.sequence_number)

    def expected_result_prefix(self) -> str:
        # TODO: Currently the server does not send updates to the worker in order of admission When
        # this is fixed (https://github.com/temporalio/temporal/pull/5831), we can make a stronger
        # assertion about the activity numbers used to construct each result.
        return f"{self.arg}-result"
