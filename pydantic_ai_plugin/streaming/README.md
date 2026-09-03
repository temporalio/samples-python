# Streaming

This sample uses the Workflow Streams support introduced by [pydantic-ai PR #6639](https://github.com/pydantic/pydantic-ai/pull/6639).

`TemporalDurability(event_stream_topic=...)` publishes typed agent events. `AgentEventStream` hosts the stream in the Workflow and keeps the Workflow alive until the terminal `AgentRunResultEvent` is acknowledged, bounded by `drain_timeout`. The consumer uses `durability.stream_agent_events(...)`; its iterator ends when the terminal event arrives and exposes an offset for reconnecting.

The topic filters token-level `PartDeltaEvent` objects to limit Workflow state. The terminal event is always retained.

```bash
uv run pydantic_ai_plugin/streaming/run_worker.py
uv run pydantic_ai_plugin/streaming/run_workflow.py
```

The producer still completes if no subscriber connects after the drain timeout. Model events published from an Activity have at-least-once delivery, so production consumers should tolerate duplicates after Activity retries.

The offline consumer prints typed event names, ending with `AgentRunResultEvent`, followed by `The durable response is complete.`

```bash
uv run --group pydantic-ai pytest tests/pydantic_ai_plugin/streaming_test.py
```
