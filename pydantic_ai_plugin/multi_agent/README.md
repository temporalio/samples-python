# Multi-agent

This sample uses Pydantic AI's programmatic handoff pattern. The researcher finishes first, then its durable result becomes input to the writer. Each model request is a separately recorded Temporal Activity, so a Worker restart resumes from completed work instead of repeating the whole pipeline.

```bash
uv run pydantic_ai_plugin/multi_agent/run_worker.py
temporal workflow execute --type MultiAgentWorkflow --task-queue pydantic-ai-multi-agent --workflow-id pydantic-ai-multi-agent-1 --input '{"topic":"How Temporal recovers from failures","model":null}'
```

Use `"model":"gateway/openai:gpt-5.2"` for a live run.

Expected offline result: `A concise explanation is ready.`

```bash
uv run --group pydantic-ai pytest tests/pydantic_ai_plugin/multi_agent_test.py
```
