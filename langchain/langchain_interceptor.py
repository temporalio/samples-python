from __future__ import annotations
import asyncio
from contextvars import copy_context

from langsmith import get_tracing_context
from langsmith.run_helpers import _set_tracing_context
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from contextlib import contextmanager
    from typing import Any, Mapping, Protocol, Type

    import temporalio.activity
    import temporalio.api.common.v1
    import temporalio.client
    import temporalio.converter
    import temporalio.worker
    import temporalio.workflow
    from langsmith import Client, trace, tracing_context
    from langsmith.run_helpers import get_current_run_tree

# Header key for LangChain context
LANGCHAIN_CONTEXT_KEY = "langchain-context"

class _InputWithHeaders(Protocol):
    headers: Mapping[str, temporalio.api.common.v1.Payload]

def set_header_from_context(
    input: _InputWithHeaders, payload_converter: temporalio.converter.PayloadConverter
) -> None:
    # Get current LangChain run tree
    run_tree = get_current_run_tree()
    if run_tree:
        headers = run_tree.to_headers()
        input.headers = {
            **input.headers,
            LANGCHAIN_CONTEXT_KEY: payload_converter.to_payload(headers),
        }

@contextmanager
def context_from_header(
    input: _InputWithHeaders, payload_converter: temporalio.converter.PayloadConverter
):
    payload = input.headers.get(LANGCHAIN_CONTEXT_KEY)
    if payload:
        run_tree = payload_converter.from_payload(payload, dict)
        # Set the run tree in the current context
        with tracing_context(parent=run_tree):
            yield
    else:
        yield

class LangChainContextPropagationInterceptor(
    temporalio.client.Interceptor, temporalio.worker.Interceptor
):
    """Interceptor that propagates LangChain context through Temporal."""

    def __init__(
        self,
        payload_converter: temporalio.converter.PayloadConverter = temporalio.converter.default().payload_converter,
    ) -> None:
        self._payload_converter = payload_converter

    def intercept_client(
        self, next: temporalio.client.OutboundInterceptor
    ) -> temporalio.client.OutboundInterceptor:
        return _LangChainContextPropagationClientOutboundInterceptor(
            next, self._payload_converter
        )

    def intercept_activity(
        self, next: temporalio.worker.ActivityInboundInterceptor
    ) -> temporalio.worker.ActivityInboundInterceptor:
        return _LangChainContextPropagationActivityInboundInterceptor(next)

    def workflow_interceptor_class(
        self, input: temporalio.worker.WorkflowInterceptorClassInput
    ) -> Type[_LangChainContextPropagationWorkflowInboundInterceptor]:
        return _LangChainContextPropagationWorkflowInboundInterceptor

class _LangChainContextPropagationClientOutboundInterceptor(
    temporalio.client.OutboundInterceptor
):
    def __init__(
        self,
        next: temporalio.client.OutboundInterceptor,
        payload_converter: temporalio.converter.PayloadConverter,
    ) -> None:
        super().__init__(next)
        self._payload_converter = payload_converter

    async def start_workflow(
        self, input: temporalio.client.StartWorkflowInput
    ) -> temporalio.client.WorkflowHandle[Any, Any]:
        with trace(name=f"start_workflow:{input.workflow}"):
            set_header_from_context(input, self._payload_converter)
            return await super().start_workflow(input)

class _LangChainContextPropagationActivityInboundInterceptor(
    temporalio.worker.ActivityInboundInterceptor
):
    async def execute_activity(
        self, input: temporalio.worker.ExecuteActivityInput
    ) -> Any:
        if isinstance(input.fn, str):
            name = input.fn
        elif callable(input.fn):
            defn = temporalio.activity._Definition.from_callable(input.fn)
            if not defn or not defn.name:
                name = "unknown"
            name = defn.name

        with context_from_header(input, temporalio.activity.payload_converter()):
            with trace(name=f"execute_activity:{name}"):
                return await self.next.execute_activity(input)

class _LangChainContextPropagationWorkflowInboundInterceptor(
    temporalio.worker.WorkflowInboundInterceptor
):
    def init(self, outbound: temporalio.worker.WorkflowOutboundInterceptor) -> None:
        self.next.init(_LangChainContextPropagationWorkflowOutboundInterceptor(outbound))

    async def execute_workflow(
        self, input: temporalio.worker.ExecuteWorkflowInput
    ) -> Any:
        if isinstance(input.run_fn, str):
            name = input.run_fn
        elif callable(input.run_fn):
            defn = temporalio.workflow._Definition.from_run_fn(input.run_fn)
            if defn is None or defn.name is None:
                name = "unknown"
            name = defn.name

        with context_from_header(input, temporalio.workflow.payload_converter()):
            # This is a sandbox friendly way to write
            # with trace(...):
            #   return await self.next.execute_workflow(input)
            with temporalio.workflow.unsafe.sandbox_unrestricted():
                t = trace(name=f"execute_workflow:{name}")
            try:
                return await self.next.execute_workflow(input)
            finally:
                with temporalio.workflow.unsafe.sandbox_unrestricted():
                    # Cannot use __aexit__ because it's internally uses 
                    # loop.run_in_executor which is not available in the sandbox
                    t.__exit__()


class _LangChainContextPropagationWorkflowOutboundInterceptor(
    temporalio.worker.WorkflowOutboundInterceptor
):
    def start_activity(
        self, input: temporalio.worker.StartActivityInput
    ) -> temporalio.workflow.ActivityHandle:
        with temporalio.workflow.unsafe.sandbox_unrestricted():
            t = trace(name=f"start_activity:{input.activity}")
        try:
            set_header_from_context(input, temporalio.workflow.payload_converter())
            return self.next.start_activity(input)
        finally:
            with temporalio.workflow.unsafe.sandbox_unrestricted():
                t.__exit__()

    async def start_child_workflow(
        self, input: temporalio.worker.StartChildWorkflowInput
    ) -> temporalio.workflow.ChildWorkflowHandle:
        with temporalio.workflow.unsafe.sandbox_unrestricted():
            t = trace(name=f"start_child_workflow:{input.workflow}")
        try:
            set_header_from_context(input, temporalio.workflow.payload_converter())
            return await self.next.start_child_workflow(input)
        finally:
            with temporalio.workflow.unsafe.sandbox_unrestricted():
                t.__exit__()