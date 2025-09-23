# Multiline Exception Logging Interceptor

This sample demonstrates how to handle multiline exception logs in Temporal workflows and activities by formatting them as single-line JSON. This solves the issue where multiline tracebacks span multiple log entries in log aggregation systems like Datadog.

## Problem

When exceptions with multiline tracebacks are raised in Temporal activities or workflows, they can create multiple separate log entries in log aggregation systems, making them difficult to parse and analyze.

## Solution

The `MultilineLoggingInterceptor` captures exceptions within Temporal boundaries and:
1. Formats the exception details as a single-line JSON object
2. Logs the formatted exception 
3. Re-raises the original exception to maintain normal error handling

The JSON format includes:
- `message`: The exception message
- `type`: The exception class name  
- `traceback`: The full traceback with newlines replaced by " | "

## Usage

```python
from multiline_logging.interceptor import MultilineLoggingInterceptor

worker = Worker(
    client,
    task_queue="my-task-queue",
    workflows=[MyWorkflow],
    activities=[my_activity],
    interceptors=[MultilineLoggingInterceptor()],
)
```

## Running the Sample

1. Start Temporal server: `temporal server start-dev`
2. Run the worker: `python multiline_logging/worker.py`
3. In another terminal, run the starter: `python multiline_logging/starter.py`

You'll see the multiline exceptions formatted as single-line JSON in the worker logs.

## Key Benefits

- **Surgical**: Only affects logging within Temporal SDK boundaries
- **Non-intrusive**: Doesn't interfere with existing log formatters
- **Preserves behavior**: Original exceptions are still raised normally
- **Structured**: JSON format is easy to parse and analyze
