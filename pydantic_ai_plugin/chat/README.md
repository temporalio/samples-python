# Agent chat

`ChatWorkflow` accepts each user turn as an Update, returns the assistant response from that Update, and keeps Pydantic AI `ModelMessage` history in Workflow state. When Temporal recommends Continue-As-New, it waits for active handlers and carries the typed history into the next run.

Assign each independent chat a unique Workflow ID. Continue-As-New keeps that ID across the whole chain automatically, so do not reuse it for an unrelated workflow.

```bash
uv run --project pydantic_ai_plugin pydantic_ai_plugin/chat/run_worker.py

WORKFLOW_ID="pydantic-ai-chat-$(uv run --project pydantic_ai_plugin python -c 'import uuid; print(uuid.uuid4())')"
temporal workflow start --type ChatWorkflow --task-queue pydantic-ai-chat --workflow-id "$WORKFLOW_ID" --input '{"messages":[],"model":null}'
temporal workflow update --workflow-id "$WORKFLOW_ID" --name turn --input '"Hello"'
temporal workflow query --workflow-id "$WORKFLOW_ID" --type message_count
temporal workflow signal --workflow-id "$WORKFLOW_ID" --name end_chat
```

For a live model, start with `{"messages":[],"model":"gateway/openai:gpt-5.2"}`.

Expected offline Update result: `Ready for the next turn.`

```bash
uv run --project pydantic_ai_plugin pytest pydantic_ai_plugin/tests/chat_test.py
```
