from dataclasses import asdict, is_dataclass
from typing import Any

from sentry_sdk import Hub, capture_exception, set_context, set_tag
from temporalio import activity
from temporalio.worker import (
    ActivityInboundInterceptor,
    ExecuteActivityInput,
    Interceptor,
)


class _SentryActivityInboundInterceptor(ActivityInboundInterceptor):
    async def execute_activity(self, input: ExecuteActivityInput) -> Any:
        # https://docs.sentry.io/platforms/python/troubleshooting/#addressing-concurrency-issues
        with Hub(Hub.current):
            set_tag("temporal.execution_type", "activity")
            set_tag("module", input.fn.__module__ + "." + input.fn.__qualname__)

            activity_info = activity.info()
            set_tag("temporal.workflow.type", activity_info.workflow_type)
            set_tag("temporal.workflow.id", activity_info.workflow_id)
            set_tag("temporal.activity.id", activity_info.activity_id)
            set_tag("temporal.activity.type", activity_info.activity_type)
            set_tag("temporal.activity.task_queue", activity_info.task_queue)
            set_tag("temporal.workflow.namespace", activity_info.workflow_namespace)
            set_tag("temporal.workflow.run_id", activity_info.workflow_run_id)
            try:
                return await super().execute_activity(input)
            except Exception as e:
                if len(input.args) == 1 and is_dataclass(input.args[0]):
                    set_context("temporal.activity.input", asdict(input.args[0]))
                set_context("temporal.activity.info", activity.info().__dict__)
                capture_exception()
                raise e


class SentryInterceptor(Interceptor):
    """Temporal Interceptor class which will report workflow & activity exceptions to Sentry"""

    def intercept_activity(
        self, next: ActivityInboundInterceptor
    ) -> ActivityInboundInterceptor:
        """Implementation of
        :py:meth:`temporalio.worker.Interceptor.intercept_activity`.
        """
        return _SentryActivityInboundInterceptor(super().intercept_activity(next))
