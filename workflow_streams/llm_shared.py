"""Types and constants for the LLM-streaming scenario.

Kept separate from ``shared.py`` because the other scenarios don't
use these — and this scenario runs on its own worker and task queue
so the ``openai`` dependency stays out of everyone else's path.
"""

from __future__ import annotations

from dataclasses import dataclass

from temporalio.contrib.workflow_streams import WorkflowStreamState

# Scenario 5 runs on its own worker so the openai dependency only
# matters for that scenario.
LLM_TASK_QUEUE = "workflow-stream-llm-task-queue"

# Topics published by the activity.
TOPIC_DELTA = "delta"
TOPIC_COMPLETE = "complete"
TOPIC_RETRY = "retry"


@dataclass
class LLMInput:
    prompt: str
    model: str = "gpt-5-mini"
    # Carries stream state across continue-as-new. None on a fresh start.
    stream_state: WorkflowStreamState | None = None


@dataclass
class TextDelta:
    text: str


@dataclass
class TextComplete:
    full_text: str


@dataclass
class RetryEvent:
    attempt: int
