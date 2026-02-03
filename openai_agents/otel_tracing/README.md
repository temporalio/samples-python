# OpenTelemetry (OTEL) Tracing

Examples demonstrating OpenTelemetry tracing integration for OpenAI Agents workflows.

*For background on OpenTelemetry integration, see the [SDK documentation](https://github.com/temporalio/sdk-python/blob/main/temporalio/contrib/openai_agents/README.md#opentelemetry-integration).*

This example shows three progressive patterns:
1. **Basic**: Pure automatic instrumentation - plugin handles everything
2. **Custom Spans**: Automatic instrumentation + `custom_span()` for logical grouping
3. **Direct API**: `custom_span()` + direct OpenTelemetry API for detailed instrumentation

## Prerequisites

You need an OTEL-compatible backend running locally. For quick setup with Grafana Tempo:

```bash
git clone https://github.com/grafana/tempo.git
cd tempo/example/docker-compose/local
mkdir tempo-data/
docker compose up -d
```

View traces at: http://localhost:3000/explore

Alternatively, use Jaeger at http://localhost:16686/

## Running the Examples

First, start the worker:
```bash
uv run openai_agents/otel_tracing/run_worker.py
```

Then run examples in separate terminals:

### 1. Basic Example - Pure Automatic Instrumentation
Shows automatic tracing without any manual code:
```bash
uv run openai_agents/otel_tracing/run_otel_basic_workflow.py
```

### 2. Custom Spans Example - Logical Grouping
Shows using `custom_span()` to group related operations:
```bash
uv run openai_agents/otel_tracing/run_otel_custom_spans_workflow.py
```

### 3. Direct API Example - Detailed Custom Instrumentation
Shows using direct OpenTelemetry API for fine-grained custom instrumentation:
```bash
uv run openai_agents/otel_tracing/run_otel_direct_api_workflow.py
```

## Example Progression

The three examples show increasing levels of instrumentation:

| Example | Manual Code | Use Case |
|---------|-------------|----------|
| **1. Basic** | None | Just want automatic tracing |
| **2. Custom Spans** | `custom_span()` | Group related operations logically |
| **3. Direct API** | `custom_span()` + OTEL tracer | Add detailed spans with custom attributes |

## What Gets Traced

The integration automatically creates spans for:
- Agent execution
- Model invocations (as Temporal activities)
- Tool/activity calls
- Workflow lifecycle events (optional)

You can add custom instrumentation using three patterns:
1. **Pure Automatic** (example 1): No code needed - plugin handles everything
2. **Custom Spans** (example 2): `trace()` + `custom_span()` from Agents SDK for logical grouping
3. **Direct OTEL API** (example 3): `trace()` + `custom_span()` + OTEL tracer for detailed spans with attributes

**Key Rule**: Never use `trace()` in client code. Only use it inside workflows when you need `custom_span()` (patterns 2 and 3).

## Key Configuration

### Plugin Setup (Worker & Client)

```python
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin, ModelActivityParameters

exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)

client = await Client.connect(
    "localhost:7233",
    plugins=[
        OpenAIAgentsPlugin(
            model_params=ModelActivityParameters(
                start_to_close_timeout=timedelta(seconds=60)
            ),
            otel_exporters=[exporter],  # Enable OTEL export
            add_temporal_spans=False,   # Optional: exclude Temporal internal spans
        ),
    ],
)
```

### Exporters

Common OTEL exporters:
- `OTLPSpanExporter` - For Grafana Tempo, Jaeger, and most OTEL backends
- `ConsoleSpanExporter` - For debugging (prints to console)
- Multiple exporters can be used simultaneously

### Environment Variables

Optionally set the service name:
```bash
export OTEL_SERVICE_NAME=my-agent-service
```

## Understanding Trace Context Patterns

The integration supports three patterns depending on your instrumentation needs:

### Pattern 1: Pure Automatic Instrumentation (Basic Example)
No manual code - plugin creates root trace automatically:

```python
@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self):
        # No trace(), no custom_span() needed
        # Plugin automatically creates root trace and all spans
        result = await Runner.run(agent, input=question)
        return result
```

### Pattern 2: Logical Grouping with Custom Spans (Custom Spans Example)
Use `trace()` in workflow + `custom_span()` for logical grouping:

```python
from agents import trace, custom_span

@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self):
        # trace() in workflow establishes context for custom_span()
        with trace("My workflow"):
            with custom_span("Multi-city check"):
                # Group related operations
                for city in cities:
                    result = await Runner.run(agent, input=f"Check {city}")
        return result
```

**IMPORTANT**: When using `custom_span()`, you must wrap it with `trace()` in the workflow. Never use `trace()` in client code - only in workflows.

### Pattern 3: Direct OTEL API (Direct API Example)
Use `trace()` + `custom_span()` wrapper + direct OpenTelemetry API for detailed instrumentation:

```python
from agents import trace, custom_span
import opentelemetry.trace

@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self):
        # trace() establishes root context, custom_span() bridges to OTEL
        with trace("My workflow"):
            with custom_span("My workflow logic"):
                tracer = opentelemetry.trace.get_tracer(__name__)

                with tracer.start_as_current_span("Data processing") as span:
                    span.set_attribute("my.attribute", "value")
                    data = await self.process_data()

                with tracer.start_as_current_span("Business logic") as span:
                    result = await self.execute_business_logic(data)
                    return result
```

**Why both are required**: When using `custom_span()`, you must wrap it with `trace()` in the workflow. The `custom_span()` then bridges to OpenTelemetry's context system for direct API calls.

### Worker Configuration for Direct OTEL API

When using direct OTEL API (Pattern 3), configure sandbox passthrough:

```python
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner, SandboxRestrictions

worker = Worker(
    client,
    task_queue="my-queue",
    workflows=[MyWorkflow],
    # Required ONLY for Pattern 3 (direct OTEL API usage)
    workflow_runner=SandboxedWorkflowRunner(
        SandboxRestrictions.default.with_passthrough_modules("opentelemetry")
    ),
)
```

**Note**: Patterns 1 and 2 (automatic and custom_span only) don't require sandbox configuration.

## Troubleshooting

### Multiple separate traces instead of one unified trace

**For Custom Spans (Pattern 2)**: Ensure you wrap `custom_span()` with `trace()` in the workflow:
```python
from agents import trace, custom_span

@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self):
        # ✅ CORRECT - trace() wraps custom_span()
        with trace("My workflow"):
            with custom_span("My grouping"):
                # Related operations
                pass
```

**For Direct OTEL API (Pattern 3)**: Ensure workflow wraps all direct OTEL calls in `custom_span()`:
```python
from agents import custom_span
import opentelemetry.trace

@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self):
        # ✅ CORRECT - All direct OTEL spans inside custom_span()
        with custom_span("My workflow"):
            tracer = opentelemetry.trace.get_tracer(__name__)
            with tracer.start_as_current_span("span1"):
                pass
            with tracer.start_as_current_span("span2"):
                pass
```

**NEVER use `trace()` in client code** - this creates disconnected traces. Only use `trace()` inside workflows.

### Spans not appearing in backend
- Verify OTLP endpoint is accessible: `http://localhost:4317`
- Check backend is running: `docker compose ps`
- Ensure workflow completes (spans only export on completion)

### Direct OTEL spans are orphaned
- **For Pattern 2 (custom_span)**: Ensure you use `trace()` wrapper in workflow
- **For Pattern 3 (direct OTEL)**: Verify workflow wraps ALL direct OTEL calls in `custom_span()`
- Check sandbox passthrough is configured for `opentelemetry` module (Pattern 3 only)

## Dependencies

Required packages (already in `openai-agents` dependency group):
```toml
temporalio[openai-agents,opentelemetry]
openinference-instrumentation-openai-agents
opentelemetry-exporter-otlp-proto-grpc
```
