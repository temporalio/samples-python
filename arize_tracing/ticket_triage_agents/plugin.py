"""Shared OpenAI Agents plugin configuration for the agents sample."""

from datetime import timedelta

from temporalio.common import RetryPolicy
from temporalio.contrib.openai_agents import ModelActivityParameters, OpenAIAgentsPlugin

TASK_QUEUE = "arize-ticket-triage-agents-task-queue"


# @@@SNIPSTART python-arize-tracing-agents-plugin
def agents_plugin() -> OpenAIAgentsPlugin:
    """The OpenAI Agents plugin, configured to export through OpenTelemetry.

    Construct it after ``setup_tracing()``: with ``use_otel_instrumentation=True``
    the plugin checks that the global tracer provider is Temporal's replay-safe
    provider, then bridges Agents SDK tracing to OpenTelemetry through the
    OpenInference ``openai-agents`` instrumentation. ``add_temporal_spans=True``
    adds CHAIN spans for the Temporal operations (start workflow, execute
    activity, ...) around the AGENT, LLM, and TOOL spans.
    """
    return OpenAIAgentsPlugin(
        use_otel_instrumentation=True,
        add_temporal_spans=True,
        model_params=ModelActivityParameters(
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=RetryPolicy(
                maximum_attempts=3, initial_interval=timedelta(seconds=1)
            ),
        ),
    )


# @@@SNIPEND
