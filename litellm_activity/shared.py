from dataclasses import dataclass

DEFAULT_MODEL = "openai/gpt-4o-mini"
TASK_QUEUE = "litellm-activity-task-queue"


@dataclass
class LLMRequest:
    """Serializable input shared by the client, Workflow, and Activity."""

    prompt: str
    model: str = DEFAULT_MODEL
    system_prompt: str = "You are a helpful assistant."
