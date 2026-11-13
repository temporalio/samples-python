# Streaming

Model output streamed to a subscriber outside the Workflow. `TemporalChatClient(streaming_topic="events")` makes a streamed call run as the `microsoft_agent_framework.invoke_model_streaming` Activity, which publishes every `ChatResponseUpdate` to the `events` topic of a `WorkflowStream` hosted on the Workflow, batched every 100 milliseconds (`streaming_batch_interval`). The Workflow still gets the whole response, so the durable result is the same as without streaming.

## What this sample demonstrates

- A `WorkflowStream()` hosted on the Workflow
- `agent.run(prompt, stream=True)` with `streaming_topic` set; without `stream=True` the call runs as the plain model Activity and publishes nothing
- `WorkflowStreamClient.subscribe(["events"])` in the starter, decoding each item with `ChatResponseUpdate.from_dict`

## Running the sample

```bash
# Terminal 1
uv run microsoft_agent_framework_plugin/streaming/run_worker.py

# Terminal 2
uv run microsoft_agent_framework_plugin/streaming/run_workflow.py
```

The starter prints the text as it arrives, then `Final result:` with the whole text. The Workflow `microsoft-agent-framework-streaming` shows one `microsoft_agent_framework.invoke_model_streaming` Activity and one Signal per published batch.

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `StreamingWorkflow` hosting a `WorkflowStream` and a `TemporalChatClient` with `streaming_topic` |
| `run_worker.py` | Registers the plugin, starts the Worker |
| `run_workflow.py` | Starts the Workflow and subscribes to the `events` topic |
