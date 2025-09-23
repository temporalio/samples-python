import json
import logging
import traceback
from typing import Any, Optional, Type

from temporalio import activity, workflow
from temporalio.worker import (
    ActivityInboundInterceptor,
    ExecuteActivityInput,
    ExecuteWorkflowInput,
    Interceptor,
    WorkflowInboundInterceptor,
    WorkflowInterceptorClassInput,
)

logger = logging.getLogger(__name__)


class _MultilineLoggingActivityInboundInterceptor(ActivityInboundInterceptor):
    async def execute_activity(self, input: ExecuteActivityInput) -> Any:
        try:
            return await super().execute_activity(input)
        except Exception as e:
            exception_data = {
                "message": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc().replace("\n", " | "),
            }

            logger.error(f"Activity exception: {json.dumps(exception_data)}")

            raise e


class _MultilineLoggingWorkflowInterceptor(WorkflowInboundInterceptor):
    async def execute_workflow(self, input: ExecuteWorkflowInput) -> Any:
        try:
            return await super().execute_workflow(input)
        except Exception as e:
            exception_data = {
                "message": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc().replace("\n", " | "),
            }

            if not workflow.unsafe.is_replaying():
                with workflow.unsafe.sandbox_unrestricted():
                    logger.error(f"Workflow exception: {json.dumps(exception_data)}")

            raise e


class MultilineLoggingInterceptor(Interceptor):
    """Temporal Interceptor that formats multiline exception logs as single-line JSON"""

    def intercept_activity(
        self, next: ActivityInboundInterceptor
    ) -> ActivityInboundInterceptor:
        return _MultilineLoggingActivityInboundInterceptor(
            super().intercept_activity(next)
        )

    def workflow_interceptor_class(
        self, input: WorkflowInterceptorClassInput
    ) -> Optional[Type[WorkflowInboundInterceptor]]:
        return _MultilineLoggingWorkflowInterceptor
