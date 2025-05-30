from __future__ import annotations

from typing import Any, Mapping, Protocol, Type

from temporalio import activity, api, client, converter, worker, workflow

with workflow.unsafe.imports_passed_through():
    from contextlib import contextmanager

    from langsmith import trace, tracing_context
    from langsmith.run_helpers import get_current_run_tree

# Header key for LangChain context
LANGCHAIN_CONTEXT_KEY = "langchain-context"


class _InputWithHeaders(Protocol):
    headers: Mapping[str, api.common.v1.Payload]


def set_header_from_context(
    input: _InputWithHeaders, payload_converter: converter.PayloadConverter
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
    input: _InputWithHeaders, payload_converter: converter.PayloadConverter
):
    payload = input.headers.get(LANGCHAIN_CONTEXT_KEY)
    if payload:
        run_tree = payload_converter.from_payload(payload, dict)
        # Set the run tree in the current context
        with tracing_context(parent=run_tree):
            yield
    else:
        yield


class LangChainContextPropagationInterceptor(client.Interceptor, worker.Interceptor):
    """Interceptor that propagates LangChain context through Temporal."""

    def __init__(
        self,
        payload_converter: converter.PayloadConverter = converter.default().payload_converter,
    ) -> None:
        self._payload_converter = payload_converter

    def intercept_client(
        self, next: client.OutboundInterceptor
    ) -> client.OutboundInterceptor:
        return _LangChainContextPropagationClientOutboundInterceptor(
            next, self._payload_converter
        )

    def intercept_activity(
        self, next: worker.ActivityInboundInterceptor
    ) -> worker.ActivityInboundInterceptor:
        return _LangChainContextPropagationActivityInboundInterceptor(next)

    def workflow_interceptor_class(
        self, input: worker.WorkflowInterceptorClassInput
    ) -> Type[_LangChainContextPropagationWorkflowInboundInterceptor]:
        return _LangChainContextPropagationWorkflowInboundInterceptor


class _LangChainContextPropagationClientOutboundInterceptor(client.OutboundInterceptor):
    def __init__(
        self,
        next: client.OutboundInterceptor,
        payload_converter: converter.PayloadConverter,
    ) -> None:
        super().__init__(next)
        self._payload_converter = payload_converter

    async def start_workflow(
        self, input: client.StartWorkflowInput
    ) -> client.WorkflowHandle[Any, Any]:
        with trace(name=f"start_workflow:{input.workflow}"):
            set_header_from_context(input, self._payload_converter)
            return await super().start_workflow(input)


class _LangChainContextPropagationActivityInboundInterceptor(
    worker.ActivityInboundInterceptor
):
    async def execute_activity(self, input: worker.ExecuteActivityInput) -> Any:
        if isinstance(input.fn, str):
            name = input.fn
        elif callable(input.fn):
            defn = activity._Definition.from_callable(input.fn)
            name = (
                defn.name if defn is not None and defn.name is not None else "unknown"
            )
        else:
            name = "unknown"

        with context_from_header(input, activity.payload_converter()):
            with trace(name=f"execute_activity:{name}"):
                return await self.next.execute_activity(input)


class _LangChainContextPropagationWorkflowInboundInterceptor(
    worker.WorkflowInboundInterceptor
):
    def init(self, outbound: worker.WorkflowOutboundInterceptor) -> None:
        self.next.init(
            _LangChainContextPropagationWorkflowOutboundInterceptor(outbound)
        )

    async def execute_workflow(self, input: worker.ExecuteWorkflowInput) -> Any:
        if isinstance(input.run_fn, str):
            name = input.run_fn
        elif callable(input.run_fn):
            defn = workflow._Definition.from_run_fn(input.run_fn)
            name = (
                defn.name if defn is not None and defn.name is not None else "unknown"
            )
        else:
            name = "unknown"

        with context_from_header(input, workflow.payload_converter()):
            # This is a sandbox friendly way to write
            # with trace(...):
            #   return await self.next.execute_workflow(input)
            with workflow.unsafe.sandbox_unrestricted():
                t = trace(
                    name=f"execute_workflow:{name}", run_id=workflow.info().run_id
                )
                with workflow.unsafe.imports_passed_through():
                    t.__enter__()
            try:
                return await self.next.execute_workflow(input)
            finally:
                with workflow.unsafe.sandbox_unrestricted():
                    # Cannot use __aexit__ because it's internally uses
                    # loop.run_in_executor which is not available in the sandbox
                    t.__exit__()


class _LangChainContextPropagationWorkflowOutboundInterceptor(
    worker.WorkflowOutboundInterceptor
):
    def start_activity(
        self, input: worker.StartActivityInput
    ) -> workflow.ActivityHandle:
        with workflow.unsafe.sandbox_unrestricted():
            t = trace(name=f"start_activity:{input.activity}", run_id=workflow.uuid4())
            with workflow.unsafe.imports_passed_through():
                t.__enter__()
        try:
            set_header_from_context(input, workflow.payload_converter())
            return self.next.start_activity(input)
        finally:
            with workflow.unsafe.sandbox_unrestricted():
                t.__exit__()

    async def start_child_workflow(
        self, input: worker.StartChildWorkflowInput
    ) -> workflow.ChildWorkflowHandle:
        with workflow.unsafe.sandbox_unrestricted():
            t = trace(
                name=f"start_child_workflow:{input.workflow}", run_id=workflow.uuid4()
            )
            with workflow.unsafe.imports_passed_through():
                t.__enter__()

        try:
            set_header_from_context(input, workflow.payload_converter())
            return await self.next.start_child_workflow(input)
        finally:
            with workflow.unsafe.sandbox_unrestricted():
                t.__exit__()
