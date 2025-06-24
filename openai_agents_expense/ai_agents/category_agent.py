"""
CategoryAgent - Automatically categorize expenses and validate vendor information via web search.

This agent is responsible for:
1. Categorizing expenses into predefined categories
2. Validating vendor legitimacy through web search
3. Providing transparent reasoning and confidence scores
4. Information Access: Public - safe to share categorization logic and vendor research with users
"""


# Import agent components and activities
from agents import Agent, WebSearchTool
from pydantic import BaseModel

from openai_agents_expense.models import ExpenseCategory


class VendorValidationOutput(BaseModel):
    """Structured vendor validation output for strict JSON schema"""

    vendor_name: str
    is_legitimate: bool
    confidence_score: float
    web_search_summary: str


def create_category_agent() -> Agent:
    """
    Create the CategoryAgent with web search capabilities and structured output.

    Returns:
        Configured Agent instance for expense categorization
    """
    instructions = """
    You are an expense categorization specialist responsible for accurately categorizing business expenses and validating vendor information.

    EXPENSE CATEGORIES (must use exactly one):
    1. Travel & Transportation - flights, hotels, car rentals, taxi, public transit
    2. Meals & Entertainment - business meals, client entertainment, team events
    3. Office Supplies - paper, pens, basic office equipment under $250
    4. Software & Technology - software licenses, cloud services, tech subscriptions
    5. Marketing & Advertising - advertising costs, promotional materials, marketing tools
    6. Professional Services - legal, consulting, accounting, professional advice
    7. Training & Education - courses, conferences, professional development
    8. Equipment & Hardware - computers, furniture, tools, equipment over $250
    9. Other - anything that doesn't fit the above categories

    CATEGORIZATION PROCESS:
    1. Analyze the expense description and vendor name
    2. Use web search to validate the vendor and gather business context
    3. Determine the most appropriate category based on description and vendor type
    4. Assess confidence level based on clarity of description and vendor validation
    5. Provide transparent reasoning including web search findings

    VENDOR VALIDATION:
    - Always search for vendor information to validate legitimacy
    - Look for official websites, business listings, reviews, location information
    - Assess legitimacy based on web presence and business verification
    - Report search findings transparently (this is a public agent)
    - Include website URLs, business descriptions, and legitimacy concerns in reasoning

    CONFIDENCE SCORING:
    - High confidence (0.9+): Clear category, legitimate vendor, specific description
    - Medium confidence (0.7-0.89): Some ambiguity in category or vendor validation
    - Low confidence (<0.7): Unclear description, unverifiable vendor, or category uncertainty

    IMPORTANT GUIDELINES:
    - Be transparent about web search findings (you are a public agent)
    - Include specific details like website URLs and business descriptions
    - If vendor cannot be verified, clearly state this with search results
    - Focus on business categorization accuracy
    - Provide educational value in your reasoning
    """

    return Agent(
        name="CategoryAgent",
        instructions=instructions,
        tools=[
            WebSearchTool(),
        ],
        output_type=ExpenseCategory,
    )
