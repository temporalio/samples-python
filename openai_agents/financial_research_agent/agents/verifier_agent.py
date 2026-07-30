from agents import Agent
from pydantic import BaseModel

# Agent to sanity-check a synthesized report for consistency and recall.
# This can be used to flag potential gaps or obvious mistakes.
VERIFIER_PROMPT = (
    "You are a meticulous auditor. You have been handed a financial analysis report. "
    "Your job is to verify the report is internally consistent, clearly sourced, and makes "
    "no unsupported claims. Point out any issues or uncertainties."
)


class VerificationResult(BaseModel):
    verified: bool
    """Whether the report seems coherent and plausible."""

    issues: str
    """If not verified, describe the main issues or concerns."""


def new_verifier_agent() -> Agent:
    return Agent(
        name="VerificationAgent",
        instructions=VERIFIER_PROMPT,
        model="gpt-4o",
        output_type=VerificationResult,
    )
