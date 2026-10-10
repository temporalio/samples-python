# Observability with Logfire

`LogfirePlugin` installs Temporal's OpenTelemetry tracing interceptor and Pydantic AI instrumentation, producing one connected trace across Workflow execution, model Activities, agent runs, and tools. The sample disables remote export when `LOGFIRE_TOKEN` is absent, so it also runs credential-free.

```bash
uv run pydantic_ai_plugin/logfire/run_worker.py
temporal workflow execute --type ObservabilityWorkflow --task-queue pydantic-ai-logfire --workflow-id pydantic-ai-logfire-1 --input '{"prompt":"Run an observable agent.","model":null}'
```

To send traces to Logfire, authenticate with `logfire auth`, export `LOGFIRE_TOKEN`, and restart the Worker. Use `"model":"gateway/openai:gpt-5.2"` for a live model.

Expected offline result: `This run is traced.` The test captures both the agent and Workflow spans in memory.

```bash
uv run --group pydantic-ai pytest tests/pydantic_ai_plugin/logfire_test.py
```
