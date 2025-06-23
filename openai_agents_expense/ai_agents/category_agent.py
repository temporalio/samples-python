"""
CategoryAgent - Automatically categorize expenses and validate vendor information via web search.

This agent is responsible for:
1. Categorizing expenses into predefined categories
2. Validating vendor legitimacy through web search
3. Providing transparent reasoning and confidence scores
4. Information Access: Public - safe to share categorization logic and vendor research with users
"""

from temporalio import workflow
# from temporalio.contrib.openai_agents.temporal_tools import activity_as_tool
from agents import WebSearchTool
from pydantic import BaseModel
from typing import Dict, Any

# Import models at module level for consistent type identity
from openai_agents_expense.models import ExpenseReport, ExpenseCategory, VendorValidation

# Import agent components and activities
with workflow.unsafe.imports_passed_through():
    from agents import Agent, Runner
    # from openai_agents_expense.activities.web_search import web_search_activity


class VendorValidationOutput(BaseModel):
    """Structured vendor validation output for strict JSON schema"""
    vendor_name: str
    is_legitimate: bool
    confidence_score: float
    web_search_summary: str


class CategoryAgentOutput(BaseModel):
    """Structured output from CategoryAgent"""
    category: str
    confidence: float
    reasoning: str
    vendor_validation: VendorValidationOutput


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
    
    The vendor_validation object should contain:
    - vendor_name: string
    - is_legitimate: boolean
    - confidence_score: float between 0 and 1
    - web_search_summary: string with search findings, URLs, and business details
    """
    
    return Agent(
        name="CategoryAgent",
        instructions=instructions,
        tools=[
            WebSearchTool(),
            # activity_as_tool(
            #     web_search_activity,
            #     start_to_close_timeout=timedelta(seconds=30),
            #     tool_name="web_search",
            #     tool_description="Search the web for vendor information and business validation"
            # )
        ],
        output_type=CategoryAgentOutput,
    )


async def categorize_expense(expense_report: ExpenseReport) -> ExpenseCategory:
    """
    Categorize an expense report using the CategoryAgent.
    
    Args:
        expense_report: The expense report to categorize
        
    Returns:
        ExpenseCategory with categorization results and vendor validation
    """
    
    # Agent start logging
    workflow.logger.info(
        f"📋 CATEGORY_AGENT_START: Starting expense categorization - "
        f"expense_id={expense_report.expense_id}, agent=CategoryAgent, "
        f"vendor={expense_report.vendor}, description={expense_report.description}, "
        f"amount=${expense_report.amount}, stage=start"
    )
    
    # Create the categorization agent
    workflow.logger.info(
        f"🤖 AGENT_CREATION: Creating CategoryAgent instance - "
        f"expense_id={expense_report.expense_id}, agent=CategoryAgent, stage=agent_creation"
    )
    
    agent = create_category_agent()
    
    # Prepare input for the agent
    expense_input = f"""
    Please categorize this expense and validate the vendor:
    
    Expense Details:
    - Description: {expense_report.description}
    - Vendor: {expense_report.vendor}
    - Amount: ${expense_report.amount}
    - Date: {expense_report.date}
    - Department: {expense_report.department}
    
    Additional Context:
    - Client Name: {expense_report.client_name or 'Not provided'}
    - Business Justification: {expense_report.business_justification or 'Not provided'}
    - International Travel: {'Yes' if expense_report.is_international_travel else 'No'}
    
    First, search for information about the vendor "{expense_report.vendor}" to validate their legitimacy and gather business context. Then categorize the expense based on the description and vendor information found.
    """
    
    workflow.logger.info(
        f"🎯 AGENT_INPUT: Prepared agent input - "
        f"expense_id={expense_report.expense_id}, agent=CategoryAgent, "
        f"vendor_to_search={expense_report.vendor}, input_length={len(expense_input)}, "
        f"stage=input_preparation"
    )
    
    # Run the agent to get categorization results
    workflow.logger.info(
        f"🚀 AGENT_EXECUTION: Running CategoryAgent - "
        f"expense_id={expense_report.expense_id}, agent=CategoryAgent, stage=execution"
    )
    
    try:
        result = await Runner.run(agent, input=expense_input)
    except Exception as e:
        workflow.logger.error(f"🚨🚨🚨 AGENT_ERROR: Error running CategoryAgent - "
                              f"expense_id={expense_report.expense_id}, agent=CategoryAgent, "
                              f"error={str(e)}")
        raise e
    
    workflow.logger.info(
        f"✅ AGENT_RESPONSE: CategoryAgent execution completed - "
        f"expense_id={expense_report.expense_id}, agent=CategoryAgent, "
        f"stage=response_received"
    )
    
    # Extract structured response from agent
    output = result.final_output
    workflow.logger.info(f"📊📊📊📊 Output: {output}")
    
    if not isinstance(output, CategoryAgentOutput):
        workflow.logger.error(
            f"🚨 INVALID_OUTPUT_TYPE: Expected CategoryAgentOutput, got {type(output)} - "
            f"expense_id={expense_report.expense_id}, agent=CategoryAgent, stage=output_validation"
        )
        raise ValueError(f"Expected CategoryAgentOutput, got {type(output)}") from e
    
    workflow.logger.info(
        f"📊 STRUCTURED_OUTPUT: Successfully received structured response - "
        f"expense_id={expense_report.expense_id}, agent=CategoryAgent, "
        f"parsed_category={output.category}, parsed_confidence={output.confidence}, "
        f"vendor_legitimate={output.vendor_validation.is_legitimate}, "
        f"stage=structured_parsing_success"
    )
    
    # Create vendor validation object from structured data
    vendor_data = output.vendor_validation
    vendor_validation = VendorValidation(
        vendor_name=vendor_data.vendor_name,
        is_legitimate=vendor_data.is_legitimate,
        confidence_score=vendor_data.confidence_score,
        web_search_summary=vendor_data.web_search_summary
    )
    
    # Create categorization result
    category_result = ExpenseCategory(
        category=output.category,
        confidence=output.confidence,
        reasoning=output.reasoning,
        vendor_validation=vendor_validation
    )
    
    workflow.logger.info(
        f"✅ CATEGORY_AGENT_SUCCESS: Categorization completed successfully - "
        f"expense_id={expense_report.expense_id}, agent=CategoryAgent, "
        f"category={category_result.category}, confidence={category_result.confidence}, "
        f"vendor_legitimate={category_result.vendor_validation.is_legitimate}, "
        f"vendor_confidence={category_result.vendor_validation.confidence_score}, stage=success"
    )
    
    return category_result
