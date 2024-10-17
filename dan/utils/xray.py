from contextlib import contextmanager

from opentelemetry.sdk.trace import Tracer


@contextmanager
def start_as_current_workflow_span(
    tracer: Tracer,
    name: str,
    method: str,
    request_type: str,
    request_payload: str,
    response_type: str,
):
    with tracer.start_as_current_span(name) as span:
        span.set_attribute("rpc.method", method)
        span.set_attribute("rpc.request.type", request_type)
        span.set_attribute("rpc.request.payload", request_payload)
        span.set_attribute("rpc.response.type", response_type)
        span.set_attribute("temporal.workflow", True)
        yield span
