import logging
from dataclasses import asdict, is_dataclass
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

with workflow.unsafe.imports_passed_through():
    import sentry_sdk


logger = logging.getLogger(__name__)


class _SentryActivityInboundInterceptor(ActivityInboundInterceptor):
    async def execute_activity(self, input: ExecuteActivityInput) -> Any:
        # https://docs.sentry.io/platforms/python/troubleshooting/#addressing-concurrency-issues
        with sentry_sdk.isolation_scope() as scope:
            scope.set_tag("temporal.execution_type", "activity")
            scope.set_tag("module", input.fn.__module__ + "." + input.fn.__qualname__)
            activity_info = activity.info()
            scope.set_tag("temporal.workflow.type", activity_info.workflow_type)
            scope.set_tag("temporal.workflow.id", activity_info.workflow_id)
            scope.set_tag("temporal.activity.id", activity_info.activity_id)
            scope.set_tag("temporal.activity.type", activity_info.activity_type)
            scope.set_tag("temporal.activity.task_queue", activity_info.task_queue)
            scope.set_tag(
                "temporal.workflow.namespace", activity_info.workflow_namespace
            )
            scope.set_tag("temporal.workflow.run_id", activity_info.workflow_run_id)
            try:
                return await super().execute_activity(input)
            except Exception as e:
                if len(input.args) == 1:
                    [arg] = input.args
                    if is_dataclass(arg) and not isinstance(arg, type):
                        scope.set_context("temporal.activity.input", asdict(arg))
                scope.set_context("temporal.activity.info", activity.info().__dict__)
                scope.capture_exception()
                raise e


class _SentryWorkflowInterceptor(WorkflowInboundInterceptor):
    async def execute_workflow(self, input: ExecuteWorkflowInput) -> Any:
        # https://docs.sentry.io/platforms/python/troubleshooting/#addressing-concurrency-issues
        with sentry_sdk.isolation_scope() as scope:
            scope.set_tag("temporal.execution_type", "workflow")
            scope.set_tag(
                "module", input.run_fn.__module__ + "." + input.run_fn.__qualname__
            )
            workflow_info = workflow.info()
            scope.set_tag("temporal.workflow.type", workflow_info.workflow_type)
            scope.set_tag("temporal.workflow.id", workflow_info.workflow_id)
            scope.set_tag("temporal.workflow.task_queue", workflow_info.task_queue)
            scope.set_tag("temporal.workflow.namespace", workflow_info.namespace)
            scope.set_tag("temporal.workflow.run_id", workflow_info.run_id)
            try:
                return await super().execute_workflow(input)
            except Exception as e:
                if len(input.args) == 1:
                    [arg] = input.args
                    if is_dataclass(arg) and not isinstance(arg, type):
                        scope.set_context("temporal.workflow.input", asdict(arg))
                scope.set_context("temporal.workflow.info", workflow.info().__dict__)
                if not workflow.unsafe.is_replaying():
                    with workflow.unsafe.sandbox_unrestricted():
                        scope.capture_exception()
                raise e


class SentryInterceptor(Interceptor):
    """Temporal Interceptor class which will report workflow & activity exceptions to Sentry"""

    def intercept_activity(
        self, next: ActivityInboundInterceptor
    ) -> ActivityInboundInterceptor:
        return _SentryActivityInboundInterceptor(super().intercept_activity(next))

    def workflow_interceptor_class(
        self, input: WorkflowInterceptorClassInput
    ) -> Optional[Type[WorkflowInboundInterceptor]]:
        return _SentryWorkflowInterceptor
