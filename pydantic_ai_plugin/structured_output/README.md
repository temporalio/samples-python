# Structured output

The agent returns `IncidentSummary`, a validated Pydantic model. `PydanticAIPlugin` installs the payload converter that preserves this type across the model Activity, Workflow state, and Workflow result.

```bash
uv run pydantic_ai_plugin/structured_output/run_worker.py
temporal workflow execute --type StructuredOutputWorkflow --task-queue pydantic-ai-structured-output --workflow-id pydantic-ai-structured-1 --input '{"prompt":"Summarize the payments incident with severity and next action.","model":null}'
```

Use `"model":"gateway/openai:gpt-5.2"` for a live run.

The offline result is a validated `IncidentSummary` for the payments service.

```bash
uv run --group pydantic-ai pytest tests/pydantic_ai_plugin/structured_output_test.py
```
