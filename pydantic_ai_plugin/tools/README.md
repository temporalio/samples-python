# Tools

This sample puts two tools behind one durable agent:

- `read_policy` is async, deterministic, and marked with `metadata={"temporal": False}`, so it runs in Workflow code.
- `lookup_inventory` represents I/O and keeps the default behavior, so Pydantic AI dispatches it as a Temporal Activity.

The model request is also an Activity. The test inspects Workflow history to verify the tool boundary.

```bash
uv run pydantic_ai_plugin/tools/run_worker.py
temporal workflow execute --type ToolsWorkflow --task-queue pydantic-ai-tools --workflow-id pydantic-ai-tools-1 --input '{"prompt":"Check policy and inventory.","model":null}'
```

Use `"model":"gateway/openai:gpt-5.2"` for a live run.

Expected offline result: `Both checks completed.`

```bash
uv run --group pydantic-ai pytest tests/pydantic_ai_plugin/tools_test.py
```
