from temporalio import workflow
from openai import AsyncOpenAI
from temporalio import activity
with workflow.unsafe.imports_passed_through():
    from braintrust import wrap_openai, init_logger


@activity.defn
async def basic_model_invocation(prompt: str) -> str:
    client = wrap_openai(AsyncOpenAI())
    logger=init_logger(project="Temporal-first-project")
    response = await client.responses.create(
        model="gpt-4o",
        instructions="You are a coding assistant that talks like a pirate.",
        input=prompt,
    )
    return response.output_text
