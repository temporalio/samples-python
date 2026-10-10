# Human in the loop

The `delete_record` tool requires approval. Pydantic AI ends the first run with `DeferredToolRequests`; the Workflow exposes the pending tool through a Query and waits durably for an `approve`, `reject`, or `cancel` Signal.

Approval resumes the agent with `DeferredToolResults`. Rejection sends `ToolDenied` back to the model. Cancellation ends the business operation without executing the tool.

```bash
uv run pydantic_ai_plugin/human_in_the_loop/run_worker.py

temporal workflow start --type ApprovalWorkflow --task-queue pydantic-ai-approval --workflow-id pydantic-ai-approval-1 --input '{"prompt":"Delete record 42.","model":null}'
temporal workflow query --workflow-id pydantic-ai-approval-1 --type pending_approval
temporal workflow signal --workflow-id pydantic-ai-approval-1 --name decide --input '"approve"'
temporal workflow show --workflow-id pydantic-ai-approval-1
```

Send `"reject"` or `"cancel"` to exercise the other paths. Use `"model":"gateway/openai:gpt-5.2"` for a live run.

Expected offline result after approval or rejection: `The operator decision was applied.` Cancellation returns `Cancelled by the operator.`

```bash
uv run --group pydantic-ai pytest tests/pydantic_ai_plugin/human_in_the_loop_test.py
```
