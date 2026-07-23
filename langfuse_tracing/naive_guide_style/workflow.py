"""ANTI-PATTERN — deliberately broken. Do not copy.

This workflow reproduces the architecture that Langfuse's Temporal guide
suggests: observability spans are created directly inside workflow code with a
plain OpenTelemetry tracer, and the worker disables the workflow sandbox to
allow it. It exists only to demonstrate, empirically, why that approach breaks
under Temporal's durable execution model. See ``ticket_triage/`` for the
correct pattern.

What goes wrong (see README.md for the experiment):

- Workflow code re-executes on every replay (worker restart, cache eviction).
  A plain tracer re-creates these spans each time with fresh random span IDs
  and re-exports them: Langfuse accumulates duplicates.
- Without Temporal's OpenTelemetry integration there is no context propagation
  into activities, so the LLM GENERATION observations land in separate,
  disconnected traces — the "nesting" is gone.
"""

import os
from dataclasses import dataclass
from datetime import timedelta

from openai import AsyncOpenAI

# ANTI-PATTERN: unrestricted imports in workflow code (the guide disables the
# sandbox entirely, so nothing stops these).
from opentelemetry import trace
from temporalio import activity, workflow


@dataclass
class ResearchStep:
    question: str


@activity.defn
async def naive_llm_step(step: ResearchStep) -> str:
    client = AsyncOpenAI(
        base_url=os.environ.get("OPENAI_BASE_URL"),
        api_key=os.environ.get("OPENAI_API_KEY"),
        max_retries=0,
    )
    response = await client.chat.completions.create(
        model=os.environ.get("MODEL_CLASSIFY", "gpt-4o-mini"),
        messages=[{"role": "user", "content": step.question}],
        timeout=30,
    )
    return response.choices[0].message.content or ""


@workflow.defn(sandboxed=False)
class NaiveGuideStyleWorkflow:
    @workflow.run
    async def run(self, topic: str) -> str:
        tracer = trace.get_tracer(__name__)
        # ANTI-PATTERN: spans created in workflow code with a plain tracer.
        # Every replay re-runs this function from the top and re-emits them.
        with tracer.start_as_current_span("research-agent"):
            with tracer.start_as_current_span("agent-step-1"):
                first = await workflow.execute_activity(
                    naive_llm_step,
                    ResearchStep(question=f"In one sentence: what is {topic}?"),
                    start_to_close_timeout=timedelta(seconds=60),
                )
            # A timer forces a second workflow task, hence a replay when the
            # workflow cache is disabled.
            await workflow.sleep(2)
            with tracer.start_as_current_span("agent-step-2"):
                second = await workflow.execute_activity(
                    naive_llm_step,
                    ResearchStep(question=f"In one sentence: why does {topic} matter?"),
                    start_to_close_timeout=timedelta(seconds=60),
                )
        return f"{first}\n{second}"
