import os
from typing import Any, cast

from agents import ModelSettings
from agents.models.interface import ModelTracing
from agents.models.openai_provider import OpenAIProvider
from openai.types.responses import ResponseOutputRefusal, ResponseOutputText
from temporalio import activity


@activity.defn
async def get_reasoning_response(
    prompt: str, model_name: str | None = None
) -> tuple[str | None, str | None]:
    """
    Activity to get response from a reasoning-capable model.
    Returns tuple of (reasoning_content, regular_content).
    """
    model_name = model_name or os.getenv("EXAMPLE_MODEL_NAME") or "deepseek-reasoner"

    provider = OpenAIProvider()
    model = provider.get_model(model_name)

    response = await model.get_response(
        system_instructions="You are a helpful assistant that explains your reasoning step by step.",
        input=prompt,
        model_settings=ModelSettings(),
        tools=[],
        output_schema=None,
        handoffs=[],
        tracing=ModelTracing.DISABLED,
        previous_response_id=None,
        prompt=None,
        conversation_id=None,
    )

    # Extract reasoning content and regular content from the response
    reasoning_content = None
    regular_content = None

    for item in response.output:
        if hasattr(item, "type") and item.type == "reasoning":
            reasoning_content = item.summary[0].text
        elif hasattr(item, "type") and item.type == "message":
            if item.content and len(item.content) > 0:
                content_item = item.content[0]
                if isinstance(content_item, ResponseOutputText):
                    regular_content = content_item.text
                elif isinstance(content_item, ResponseOutputRefusal):
                    refusal_item = cast(Any, content_item)
                    regular_content = refusal_item.refusal

    return reasoning_content, regular_content
