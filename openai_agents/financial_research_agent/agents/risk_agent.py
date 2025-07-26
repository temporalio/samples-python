from agents import Agent
from pydantic import BaseModel

# A sub-agent specializing in identifying risk factors or concerns.
RISK_PROMPT = (
    "You are a risk analyst looking for potential red flags in a company's outlook. "
    "Given background research, produce a short analysis of risks such as competitive threats, "
    "regulatory issues, supply chain problems, or slowing growth. Keep it under 2 paragraphs."
)


class AnalysisSummary(BaseModel):
    summary: str
    """Short text summary for this aspect of the analysis."""


def new_risk_agent() -> Agent:
    return Agent(
        name="RiskAnalystAgent",
        instructions=RISK_PROMPT,
        output_type=AnalysisSummary,
    )
