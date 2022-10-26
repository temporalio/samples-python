from dataclasses import asdict, is_dataclass
from typing import Any, Optional, Type

import sentry_sdk
from temporalio import workflow
from temporalio.worker import (
    ActivityInboundInterceptor,
    ExecuteActivityInput,
    ExecuteWorkflowInput,
    Interceptor,
    WorkflowInboundInterceptor,
    WorkflowInterceptorClassInput,
)


class _SentryActivityInboundInterceptor(ActivityInboundInterceptor):
    async def execute_activity(self, input: ExecuteActivityInput) -> Any:
        transaction_name = input.fn.__module__ + "." + input.fn.__name__
        scope_ctx_manager = sentry_sdk.configure_scope()
        with scope_ctx_manager as scope, sentry_sdk.start_transaction(
            name=transaction_name
        ):
            sentry_sdk.set_tag("temporal.execution_type", "activity")
            sentry_sdk.set_tag("temporal.activity.name", input.fn.__name__)
            try:
                return await super().execute_activity(input)
            except Exception as e:
                if len(input.args) == 1 and is_dataclass(input.args[0]):
                    sentry_sdk.set_context(
                        "temporal.activity.input", asdict(input.args[0])
                    )
                sentry_sdk.capture_exception(e)
                raise e
            finally:
                scope.clear()


class _SentryWorkflowInterceptor(WorkflowInboundInterceptor):
    async def execute_workflow(self, input: ExecuteWorkflowInput) -> Any:
        transaction_name = input.type.__module__ + "." + input.type.__name__
        scope_ctx_manager = sentry_sdk.configure_scope()
        with scope_ctx_manager as scope, sentry_sdk.start_transaction(
            name=transaction_name
        ):
            sentry_sdk.set_tag("temporal.execution_type", "workflow")
            sentry_sdk.set_tag("temporal.workflow.name", input.type.__name__)
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
