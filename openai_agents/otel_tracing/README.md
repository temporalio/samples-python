# OpenTelemetry (OTEL) Tracing for OpenAI Agents

This example demonstrates how to instrument OpenAI Agents workflows with OpenTelemetry (OTEL) for distributed tracing and observability.

Traces can be exported to any OTEL-compatible backend such as Jaeger, Grafana Tempo, Datadog, New Relic, or other tracing systems.

## Overview

The Temporal OpenAI Agents SDK provides built-in OTEL integration that:
- **Automatically instruments** agent runs, model calls, and activities
- **Is replay-safe** - spans are only exported when workflows actually complete (not during replay)
- **Provides deterministic IDs** - consistent span/trace IDs across workflow replays
- **Supports multiple exporters** - send traces to multiple backends simultaneously

## Two Instrumentation Patterns

### 1. Automatic Instrumentation (Recommended for Most Users)

The SDK automatically creates spans for:
- Agent execution
- Model invocations (as Temporal activities)
- Tool/activity calls
- Workflow lifecycle events

**Use this when:** You want visibility into agent behavior without custom instrumentation.

See `run_otel_basic.py` for an example.

### 2. Direct OTEL API Usage (Advanced)

You can use the OpenTelemetry API directly in workflows to:
- Instrument custom business logic
- Add domain-specific spans and attributes
- Integrate with organization-wide OTEL conventions
- Monitor performance of specific operations

**Use this when:** You need to trace custom workflow logic beyond agent/model calls.

See `run_otel_direct_api.py` for an example.

## Quick Start

### Prerequisites

Ensure you have an OTEL collector or backend running. For local testing with Grafana Tempo:

```bash
git clone https://github.com/grafana/tempo.git
cd tempo/example/docker-compose/local
mkdir tempo-data/
docker compose up -d
```

View traces at: http://localhost:3000/explore

### Install Dependencies

```bash
uv sync
```

### Start the Worker

```bash
uv run openai_agents/otel_tracing/run_worker.py
```

### Run Examples

In separate terminals:

**Basic automatic instrumentation:**
```bash
uv run openai_agents/otel_tracing/run_otel_basic.py
```

**Direct OTEL API usage:**
```bash
uv run openai_agents/otel_tracing/run_otel_direct_api.py
```

## Implementation Details

### Plugin Configuration

Configure OTEL exporters in the `OpenAIAgentsPlugin`:

```python
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin

client = await Client.connect(
    "localhost:7233",
    plugins=[
        OpenAIAgentsPlugin(
            model_params=ModelActivityParameters(
                start_to_close_timeout=timedelta(seconds=30)
            ),
            otel_exporters=[
                OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
            ],
            add_temporal_spans=False,  # Optional: exclude Temporal internal spans
        ),
    ],
)
```

### Key Parameters

**`otel_exporters`**: List of OTEL span exporters
- `OTLPSpanExporter` - OTLP protocol (most common)
- `InMemorySpanExporter` - For testing
- `ConsoleSpanExporter` - Debug output
- Multiple exporters supported simultaneously

**`add_temporal_spans`**: Whether to include Temporal internal spans (default: `True`)
- `False` - Cleaner traces focused on agent logic
- `True` - Full visibility including Temporal internals (startWorkflow, executeActivity, etc.)

### Direct OTEL API Usage

**CRITICAL REQUIREMENTS** for using `opentelemetry.trace` API directly in workflows:

#### 1. Wrap in `custom_span()` from Agents SDK

Direct OTEL calls **MUST** be wrapped in `custom_span()` to establish the bridge between Agent SDK trace context and OTEL context:

```python
from agents import custom_span
import opentelemetry.trace

@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self):
        # ✅ CORRECT - custom_span establishes OTEL context
        with custom_span("My workflow logic"):
            tracer = opentelemetry.trace.get_tracer(__name__)
            with tracer.start_as_current_span("custom-instrumentation") as span:
                span.set_attribute("business.metric", 42)
                # This span will be properly parented
                result = await my_business_logic()

        # ❌ WRONG - becomes orphaned root span, disconnected from trace
        tracer = opentelemetry.trace.get_tracer(__name__)
        with tracer.start_as_current_span("orphaned-span"):
            # No connection to the agent trace!
            pass
```

#### 2. Configure Sandbox Passthrough

The `opentelemetry` module must be allowed in the workflow sandbox:

```python
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import (
    SandboxedWorkflowRunner,
    SandboxRestrictions,
)

worker = Worker(
    client,
    task_queue="otel-task-queue",
    workflows=[MyWorkflow],
    workflow_runner=SandboxedWorkflowRunner(
        SandboxRestrictions.default.with_passthrough_modules("opentelemetry")
    ),
)
```

### Trace Context Propagation

Traces automatically propagate through the system:

```
Client trace
    └─> Workflow execution
        ├─> Agent span
        │   └─> Model activity
        ├─> Custom span (if using direct API)
        └─> Tool activity
```

- **Client → Workflow**: Trace context propagates when starting workflow within `trace()` block
- **Workflow → Activity**: Context automatically propagates to activities
- **Replay-safe**: Spans only export on actual completion, not during replay

### Environment Configuration

Set the OTEL service name (optional):
```bash
export OTEL_SERVICE_NAME=my-agent-service
```

## Common Use Cases

### Basic Monitoring
Use automatic instrumentation to:
- Monitor agent performance
- Debug agent behavior
- Track model API usage
- Identify bottlenecks

### Custom Business Logic
Use direct OTEL API to:
- Instrument domain-specific operations
- Add business metrics as span attributes
- Create logical groupings of related operations
- Integrate with existing observability stack

### Production Observability
- Export to multiple backends (e.g., Jaeger for dev, Datadog for prod)
- Use `add_temporal_spans=False` for cleaner production traces
- Add custom attributes for filtering/grouping in your observability tool

## Troubleshooting

### Spans not appearing in backend
- Verify OTLP endpoint is accessible
- Check that backend is configured to accept OTLP
- Ensure workflow completes (spans only export on completion)

### Direct OTEL spans become root spans
- Verify you're wrapping calls in `custom_span()`
- Check sandbox passthrough is configured
- Ensure you're within an existing trace context

### Duplicate spans across replays
- This is expected behavior during development with workflow cache
- Spans are only exported once per actual execution, not per replay

## Related Examples

- [grafana-tempo-openai-example](../../../../grafana-tempo-openai-example/) - End-to-end observability demo
- [basic/](../basic/) - Simple agent examples without OTEL
- [financial_research_agent](../financial_research_agent/) - Complex multi-agent example
