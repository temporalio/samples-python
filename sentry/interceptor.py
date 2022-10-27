from dataclasses import asdict, is_dataclass
from typing import Any, Optional, Type

import sentry_sdk
from temporalio import workflow, activity
from temporalio.worker import (
    ActivityInboundInterceptor,
    ExecuteActivityInput,
    ExecuteWorkflowInput,
    Interceptor,
    WorkflowInboundInterceptor,
    WorkflowInterceptorClassInput,
)


def _set_common_workflow_tags(
    info: workflow.Info | activity.Info,
):
    sentry_sdk.set_tag("temporal.workflow.namespace", info.workflow_namespace)
    sentry_sdk.set_tag("temporal.workflow.type", info.workflow_type)
    sentry_sdk.set_tag("temporal.workflow.id", info.workflow_id)
    sentry_sdk.set_tag("temporal.workflow.run_id", info.run_id)


class _SentryActivityInboundInterceptor(ActivityInboundInterceptor):
    async def execute_activity(self, input: ExecuteActivityInput) -> Any:
        transaction_name = input.fn.__module__ + "." + input.fn.__qualname__
        scope_ctx_manager = sentry_sdk.configure_scope()
        with scope_ctx_manager as scope, sentry_sdk.start_transaction(
            name=transaction_name
        ):
            sentry_sdk.set_tag("temporal.execution_type", "activity")
            activity_info = activity.info()
            _set_common_workflow_tags(activity_info)
            sentry_sdk.set_tag("temporal.activity.id", activity_info.activity_id)
            sentry_sdk.set_tag("temporal.activity.type", activity_info.activity_type)
            sentry_sdk.set_tag("temporal.activity.task_queue", activity_info.task_queue)
            try:
                return await super().execute_activity(input)
            except Exception as e:
                if len(input.args) == 1 and is_dataclass(input.args[0]):
                    sentry_sdk.set_context(
                        "temporal.activity.input", asdict(input.args[0])
                    )
                sentry_sdk.set_context(
                    "temporal.activity.info", activity.info().__dict__
                )
                sentry_sdk.capture_exception(e)
                raise e
            finally:
                scope.clear()


class _SentryWorkflowInterceptor(WorkflowInboundInterceptor):
    async def execute_workflow(self, input: ExecuteWorkflowInput) -> Any:
        transaction_name = input.fn.__module__ + "." + input.fn.__qualname__
        scope_ctx_manager = sentry_sdk.configure_scope()
        with scope_ctx_manager as scope, sentry_sdk.start_transaction(
            name=transaction_name
        ):
            sentry_sdk.set_tag("temporal.execution_type", "workflow")
            workflow_info = workflow.info()
            _set_common_workflow_tags(workflow_info)
            sentry_sdk.set_tag("temporal.workflow.task_queue", workflow_info.task_queue)
            try:
                return await super().execute_workflow(input)
            except Exception as e:
                if len(input.args) == 1 and is_dataclass(input.args[0]):
                    sentry_sdk.set_context(
                        "temporal.workflow.input", asdict(input.args[0])
                    )
                sentry_sdk.set_context(
                    "temporal.workflow.info", workflow.info().__dict__
                )
                sentry_sdk.capture_exception(e)
                raise e
            finally:
                scope.clear()


class SentryInterceptor(Interceptor):
    """Temporal Interceptor class which will report workflow & activity exceptions to Sentry"""

    def intercept_activity(
        self, next: ActivityInboundInterceptor
    ) -> ActivityInboundInterceptor:
        """Implementation of
        :py:meth:`temporalio.worker.Interceptor.intercept_activity`.
        """
        return _SentryActivityInboundInterceptor(super().intercept_activity(next))

    def workflow_interceptor_class(
        self, input: WorkflowInterceptorClassInput
    ) -> Optional[Type[WorkflowInboundInterceptor]]:
        return _SentryWorkflowInterceptor
