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
    
    # Agent start logging
    logger.info(
        f"📋 CATEGORY_AGENT_START: Starting expense categorization",
        extra={
            "expense_id": expense_report.expense_id,
            "agent": "CategoryAgent",
            "vendor": expense_report.vendor,
            "description": expense_report.description,
            "amount": str(expense_report.amount),
            "stage": "start"
        }
    )
    
    # Create the categorization agent
    logger.info(
        f"🤖 AGENT_CREATION: Creating CategoryAgent instance",
        extra={
            "expense_id": expense_report.expense_id,
            "agent": "CategoryAgent",
            "stage": "agent_creation"
        }
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
    
    logger.info(
        f"🎯 AGENT_INPUT: Prepared agent input",
        extra={
            "expense_id": expense_report.expense_id,
            "agent": "CategoryAgent",
            "vendor_to_search": expense_report.vendor,
            "input_length": len(expense_input),
            "stage": "input_preparation"
        }
    )
    
    try:
        # Run the agent to get categorization results
        logger.info(
            f"🚀 AGENT_EXECUTION: Running CategoryAgent",
            extra={
                "expense_id": expense_report.expense_id,
                "agent": "CategoryAgent",
                "stage": "execution"
            }
        )
        
        result = await Runner.run(agent, input=expense_input)
        
        logger.info(
            f"✅ AGENT_RESPONSE: CategoryAgent execution completed",
            extra={
                "expense_id": expense_report.expense_id,
                "agent": "CategoryAgent",
                "response_length": len(result.final_output) if hasattr(result, 'final_output') else 0,
                "stage": "response_received"
            }
        )
        
        # Parse the agent's response
        import json
        
        try:
            # Extract JSON from the agent's response
            response_text = result.final_output
            
            logger.info(
                f"🔍 RESPONSE_PARSING: Parsing agent response",
                extra={
                    "expense_id": expense_report.expense_id,
                    "agent": "CategoryAgent",
                    "response_text_length": len(response_text),
                    "stage": "response_parsing"
                }
            )
            
            # Find JSON in the response (agent might include additional text)
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                parsed_result = json.loads(json_text)
                
                logger.info(
                    f"📊 JSON_PARSED: Successfully parsed agent response",
                    extra={
                        "expense_id": expense_report.expense_id,
                        "agent": "CategoryAgent",
                        "parsed_category": parsed_result.get("category", "unknown"),
                        "parsed_confidence": parsed_result.get("confidence", 0.0),
                        "vendor_legitimate": parsed_result.get("vendor_validation", {}).get("is_legitimate", False),
                        "stage": "json_parsing_success"
                    }
                )
                
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
                
                logger.info(
                    f"✅ CATEGORY_AGENT_SUCCESS: Categorization completed successfully",
                    extra={
                        "expense_id": expense_report.expense_id,
                        "agent": "CategoryAgent",
                        "category": category_result.category,
                        "confidence": category_result.confidence,
                        "vendor_legitimate": category_result.vendor_validation.is_legitimate,
                        "vendor_confidence": category_result.vendor_validation.confidence_score,
                        "stage": "success"
                    }
                )
                
                return category_result
                
            else:
                raise ValueError("No valid JSON found in agent response")
                
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(
                f"🚨 PARSING_ERROR: Failed to parse CategoryAgent response",
                extra={
                    "expense_id": expense_report.expense_id,
                    "agent": "CategoryAgent",
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "response_preview": result.final_output[:200] if hasattr(result, 'final_output') else "No output",
                    "stage": "parsing_error"
                }
            )
            
            # Create fallback result with low confidence
            fallback_category = _fallback_categorization(expense_report)
            
            logger.warning(
                f"⚠️ CATEGORY_FALLBACK: Using fallback categorization due to parsing error",
                extra={
                    "expense_id": expense_report.expense_id,
                    "agent": "CategoryAgent",
                    "fallback_category": fallback_category.category,
                    "fallback_confidence": fallback_category.confidence,
                    "stage": "fallback_parsing"
                }
            )
            
            return fallback_category
            
    except Exception as e:
        logger.error(
            f"🚨 CATEGORY_AGENT_ERROR: CategoryAgent execution failed",
            extra={
                "expense_id": expense_report.expense_id,
                "agent": "CategoryAgent",
                "error": str(e),
                "error_type": type(e).__name__,
                "stage": "execution_error"
            }
        )
        
        # Create fallback result
        fallback_category = _fallback_categorization(expense_report)
        
        logger.warning(
            f"⚠️ CATEGORY_FALLBACK: Using fallback categorization due to agent failure",
            extra={
                "expense_id": expense_report.expense_id,
                "agent": "CategoryAgent",
                "fallback_category": fallback_category.category,
                "fallback_confidence": fallback_category.confidence,
                "stage": "fallback_execution"
            }
        )
        
        return fallback_category


def _fallback_categorization(expense_report: ExpenseReport) -> ExpenseCategory:
    """
    Provide fallback categorization when the agent fails.
    
    Args:
        expense_report: The expense report to categorize
        
    Returns:
        Basic ExpenseCategory with low confidence
    """
    logger = workflow.logger
    
    logger.info(
        f"🔧 FALLBACK_START: Starting fallback categorization",
        extra={
            "expense_id": expense_report.expense_id,
            "agent": "CategoryAgent",
            "fallback_method": "keyword_based",
            "stage": "fallback_start"
        }
    )
    
    # Simple keyword-based fallback categorization
    description_lower = expense_report.description.lower()
    vendor_lower = expense_report.vendor.lower()
    
    logger.info(
        f"🔍 KEYWORD_ANALYSIS: Analyzing keywords for categorization",
        extra={
            "expense_id": expense_report.expense_id,
            "agent": "CategoryAgent",
            "description": description_lower,
            "vendor": vendor_lower,
            "stage": "keyword_analysis"
        }
    )
    
    if any(word in description_lower for word in ["flight", "hotel", "travel", "taxi", "uber"]):
        category = "Travel & Transportation"
        matching_keywords = [word for word in ["flight", "hotel", "travel", "taxi", "uber"] if word in description_lower]
    elif any(word in description_lower for word in ["meal", "lunch", "dinner", "restaurant"]):
        category = "Meals & Entertainment"
        matching_keywords = [word for word in ["meal", "lunch", "dinner", "restaurant"] if word in description_lower]
    elif any(word in description_lower for word in ["office", "supplies", "paper", "pen"]):
        category = "Office Supplies"
        matching_keywords = [word for word in ["office", "supplies", "paper", "pen"] if word in description_lower]
    elif any(word in description_lower for word in ["software", "subscription", "license", "cloud"]):
        category = "Software & Technology"
        matching_keywords = [word for word in ["software", "subscription", "license", "cloud"] if word in description_lower]
    elif any(word in description_lower for word in ["equipment", "computer", "hardware"]):
        category = "Equipment & Hardware"
        matching_keywords = [word for word in ["equipment", "computer", "hardware"] if word in description_lower]
    elif any(word in description_lower for word in ["consulting", "legal", "professional"]):
        category = "Professional Services"
        matching_keywords = [word for word in ["consulting", "legal", "professional"] if word in description_lower]
    elif any(word in description_lower for word in ["training", "education", "course", "conference"]):
        category = "Training & Education"
        matching_keywords = [word for word in ["training", "education", "course", "conference"] if word in description_lower]
    elif any(word in description_lower for word in ["marketing", "advertising", "promotion"]):
        category = "Marketing & Advertising"
        matching_keywords = [word for word in ["marketing", "advertising", "promotion"] if word in description_lower]
    else:
        category = "Other"
        matching_keywords = []
    
    logger.info(
        f"🎯 CATEGORY_DETERMINED: Fallback category determined",
        extra={
            "expense_id": expense_report.expense_id,
            "agent": "CategoryAgent",
            "determined_category": category,
            "matching_keywords": matching_keywords,
            "stage": "category_determination"
        }
    )
    
    # Create basic vendor validation with low confidence
    vendor_validation = VendorValidation(
        vendor_name=expense_report.vendor,
        is_legitimate=False,  # Cannot verify without web search
        confidence_score=0.3,
        web_search_summary=f"Fallback categorization - vendor {expense_report.vendor} could not be verified due to agent processing failure."
    )
    
    fallback_result = ExpenseCategory(
        category=category,
        confidence=0.4,  # Low confidence for fallback
        reasoning=f"Fallback categorization based on keywords in description. Original agent processing failed. Category '{category}' assigned based on description '{expense_report.description}' but vendor validation was not performed.",
        vendor_validation=vendor_validation
    )
    
    logger.info(
        f"✅ FALLBACK_COMPLETE: Fallback categorization completed",
        extra={
            "expense_id": expense_report.expense_id,
            "agent": "CategoryAgent",
            "fallback_category": fallback_result.category,
            "fallback_confidence": fallback_result.confidence,
            "vendor_legitimate": fallback_result.vendor_validation.is_legitimate,
            "stage": "fallback_complete"
        }
    )
    
    return fallback_result 