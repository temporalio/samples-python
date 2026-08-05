from litellm import ModelResponse, acompletion
from temporalio import activity

from litellm_activity.shared import LLMRequest


@activity.defn
async def call_litellm(request: LLMRequest) -> str:
    """Make the nondeterministic network call outside Workflow code."""
    response = await acompletion(
        model=request.model,
        messages=[
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.prompt},
        ],
        timeout=30,
        # Let Temporal own retries so every attempt is visible in Event History.
        num_retries=0,
    )

    if not isinstance(response, ModelResponse):
        raise TypeError("Expected a non-streaming LiteLLM response")

    content = response.choices[0].message.content
    if not content:
        raise ValueError("LiteLLM returned an empty response")
    return content
