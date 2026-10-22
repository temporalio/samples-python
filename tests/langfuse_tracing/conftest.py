from typing import Iterator

import opentelemetry.trace
import pytest
from opentelemetry.util._once import Once


@pytest.fixture
def reset_otel_tracer_provider() -> Iterator[None]:
    """Reset global OpenTelemetry tracer provider state around a test.

    OpenTelemetry only allows the global tracer provider to be set once per
    process; tests that install their own provider need this reset.
    """
    opentelemetry.trace._TRACER_PROVIDER_SET_ONCE = Once()
    opentelemetry.trace._TRACER_PROVIDER = None
    yield
    opentelemetry.trace._TRACER_PROVIDER_SET_ONCE = Once()
    opentelemetry.trace._TRACER_PROVIDER = None
