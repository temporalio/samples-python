"""
CategoryAgent - Automatically categorize expenses and validate vendor information via web search.

This agent is responsible for:
1. Categorizing expenses into predefined categories
2. Validating vendor legitimacy through web search
3. Providing transparent reasoning and confidence scores
4. Information Access: Public - safe to share categorization logic and vendor research with users
"""

from datetime import timedelta
from temporalio import workflow
from temporalio.contrib.openai_agents.temporal_tools import activity_as_tool

# Import agent components and activities
with workflow.unsafe.imports_passed_through():
    from agents import Agent, Runner
    from openai_agents_expense.activities.web_search import web_search_activity
    from openai_agents_expense.models import ExpenseReport, ExpenseCategory, VendorValidation


def create_category_agent() -> Agent:
    """
    Create the CategoryAgent with web search capabilities.
    
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

    RESPONSE FORMAT:
    Always respond with a JSON object containing:
    {
        "category": "exact category name from the 9 options",
        "confidence": float between 0 and 1,
        "reasoning": "detailed explanation including web search findings",
        "vendor_validation": {
            "vendor_name": "vendor name",
            "is_legitimate": boolean,
            "confidence_score": float between 0 and 1,
            "web_search_summary": "summary of web search findings with URLs and business details"
        }
    }

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
            activity_as_tool(
                web_search_activity,
                start_to_close_timeout=timedelta(seconds=30),
                tool_name="web_search",
                tool_description="Search the web for vendor information and business validation"
            )
        ]
    )


async def categorize_expense(expense_report: ExpenseReport) -> ExpenseCategory:
    """
    Categorize an expense report using the CategoryAgent.
    
    Args:
        expense_report: The expense report to categorize
        
    Returns:
        ExpenseCategory with categorization results and vendor validation
    """
    logger = workflow.logger
    logger.info(f"Categorizing expense {expense_report.expense_id}")
    
    # Create the categorization agent
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
    
    try:
        # Run the agent to get categorization results
        result = await Runner.run(agent, input=expense_input)
        
        # Parse the agent's response
        import json
        
        try:
            # Extract JSON from the agent's response
            response_text = result.final_output
            
            # Find JSON in the response (agent might include additional text)
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                parsed_result = json.loads(json_text)
                
                # Create vendor validation object
                vendor_validation = VendorValidation(
                    vendor_name=parsed_result["vendor_validation"]["vendor_name"],
                    is_legitimate=parsed_result["vendor_validation"]["is_legitimate"],
                    confidence_score=parsed_result["vendor_validation"]["confidence_score"],
                    web_search_summary=parsed_result["vendor_validation"]["web_search_summary"]
                )
                
                # Create categorization result
                category_result = ExpenseCategory(
                    category=parsed_result["category"],
                    confidence=parsed_result["confidence"],
                    reasoning=parsed_result["reasoning"],
                    vendor_validation=vendor_validation
                )
                
                logger.info(f"Categorization completed: {category_result.category} (confidence: {category_result.confidence})")
                return category_result
                
            else:
                raise ValueError("No valid JSON found in agent response")
                
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Failed to parse agent response: {e}")
            logger.error(f"Agent response was: {result.final_output}")
            
            # Create fallback result with low confidence
            fallback_category = _fallback_categorization(expense_report)
            logger.warning(f"Using fallback categorization: {fallback_category.category}")
            return fallback_category
            
    except Exception as e:
        logger.error(f"CategoryAgent failed for expense {expense_report.expense_id}: {e}")
        
        # Create fallback result
        fallback_category = _fallback_categorization(expense_report)
        logger.warning(f"Using fallback categorization due to agent failure: {fallback_category.category}")
        return fallback_category


def _fallback_categorization(expense_report: ExpenseReport) -> ExpenseCategory:
    """
    Provide fallback categorization when the agent fails.
    
    Args:
        expense_report: The expense report to categorize
        
    Returns:
        Basic ExpenseCategory with low confidence
    """
    # Simple keyword-based fallback categorization
    description_lower = expense_report.description.lower()
    vendor_lower = expense_report.vendor.lower()
    
    if any(word in description_lower for word in ["flight", "hotel", "travel", "taxi", "uber"]):
        category = "Travel & Transportation"
    elif any(word in description_lower for word in ["meal", "lunch", "dinner", "restaurant"]):
        category = "Meals & Entertainment"
    elif any(word in description_lower for word in ["office", "supplies", "paper", "pen"]):
        category = "Office Supplies"
    elif any(word in description_lower for word in ["software", "subscription", "license", "cloud"]):
        category = "Software & Technology"
    elif any(word in description_lower for word in ["equipment", "computer", "hardware"]):
        category = "Equipment & Hardware"
    elif any(word in description_lower for word in ["consulting", "legal", "professional"]):
        category = "Professional Services"
    elif any(word in description_lower for word in ["training", "education", "course", "conference"]):
        category = "Training & Education"
    elif any(word in description_lower for word in ["marketing", "advertising", "promotion"]):
        category = "Marketing & Advertising"
    else:
        category = "Other"
    
    # Create basic vendor validation with low confidence
    vendor_validation = VendorValidation(
        vendor_name=expense_report.vendor,
        is_legitimate=False,  # Cannot verify without web search
        confidence_score=0.3,
        web_search_summary=f"Fallback categorization - vendor {expense_report.vendor} could not be verified due to agent processing failure."
    )
    
    return ExpenseCategory(
        category=category,
        confidence=0.4,  # Low confidence for fallback
        reasoning=f"Fallback categorization based on keywords in description. Original agent processing failed. Category '{category}' assigned based on description '{expense_report.description}' but vendor validation was not performed.",
        vendor_validation=vendor_validation
    ) 