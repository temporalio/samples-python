from dataclasses import dataclass


@dataclass
class LLMRequest:
    """Serializable input shared by the client, Workflow, and Activity."""

    prompt: str
    model: str = "openai/gpt-4o-mini"
    system_prompt: str = "You are a helpful assistant."
