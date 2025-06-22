"""
Pydantic data models for the OpenAI Agents Expense Processing Sample.

These models define the structured data types used throughout the expense processing workflow,
including expense reports, agent outputs, and decision results.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel


class ExpenseReport(BaseModel):
    """
    Core expense report data submitted by employees.
    """
    expense_id: str
    amount: Decimal
    description: str
    vendor: str
    date: date  # When the expense occurred
    department: str
    employee_id: str
    # Enhanced fields for business rule support
    receipt_provided: bool  # For receipt requirements over $75 (trust this flag)
    submission_date: date  # To detect late submissions (>60 days)
    client_name: Optional[str] = None  # Required for entertainment expenses
    business_justification: Optional[str] = None  # Required for entertainment expenses
    is_international_travel: bool = False  # Requires human approval regardless of amount


class VendorValidation(BaseModel):
    """
    Results of vendor validation through web search.
    """
    vendor_name: str
    is_legitimate: bool
    confidence_score: float
    web_search_summary: str  # Summary of web search findings: website URLs, business description, 
                            # company information, search result quality ("clear", "conflicting", "missing", "insufficient"),
                            # and any public legitimacy concerns or verification details


class ExpenseCategory(BaseModel):
    """
    Categorization results from CategoryAgent.
    """
    category: str  # One of: "Travel & Transportation", "Meals & Entertainment", "Office Supplies", 
                  # "Software & Technology", "Marketing & Advertising", "Professional Services", 
                  # "Training & Education", "Equipment & Hardware", "Other"
    confidence: float
    reasoning: str  # Includes vendor validation details: website URLs, business description summary, 
                   # company information found via web search, and any public legitimacy concerns
    vendor_validation: VendorValidation


class PolicyViolation(BaseModel):
    """
    Individual policy violation details.
    """
    rule_name: str
    violation_type: str
    severity: str  # "warning", "requires_review", "rejection"
    details: str
    threshold_amount: Optional[Decimal] = None  # For dollar-based thresholds


class PolicyEvaluation(BaseModel):
    """
    Policy evaluation results from PolicyEvaluationAgent.
    """
    compliant: bool
    violations: List[PolicyViolation]
    reasoning: str
    requires_human_review: bool  # Based on policy complexity, not fraud
    mandatory_human_review: bool  # Based on mandatory escalation rules
    policy_explanation: str  # Clear explanation of applicable policies
    confidence: float


class FraudFlag(BaseModel):
    """
    Individual fraud detection flag.
    """
    flag_type: str
    risk_level: str  # "low", "medium", "high"
    details: str  # Carefully sanitized to not reveal detection methods


class FraudAssessment(BaseModel):
    """
    Fraud assessment results from FraudAgent (Private - security critical).
    """
    overall_risk: str  # "low", "medium", "high"
    flags: List[FraudFlag]
    reasoning: str  # Heavily guarded to not reveal detection methods
    requires_human_review: bool  # Based on fraud risk level
    confidence: float
    vendor_risk_indicators: List[str]  # Private risk indicators derived from analysis


class FinalDecision(BaseModel):
    """
    Final decision from DecisionOrchestrationAgent.
    """
    decision: str  # "approved", "requires_human_review", "final_rejection", "rejected_with_instructions"
    internal_reasoning: str  # Detailed reasoning for administrators, includes fraud context
    external_reasoning: str  # Sanitized reasoning for users, no fraud details exposed
    escalation_reason: Optional[str] = None  # Generic reason for human escalation
    is_mandatory_escalation: bool  # Whether escalation is due to mandatory rules
    confidence: float  # Overall confidence in the decision


class ExpenseResponse(BaseModel):
    """
    Final response message from ResponseAgent.
    """
    message: str
    decision_summary: str  # Includes any resubmission instructions when applicable
    policy_explanation: Optional[str]  # Clear policy explanations when relevant
    categorization_summary: str  # Summary of categorization and vendor validation


class ExpenseStatus(BaseModel):
    """
    Current status of expense processing.
    """
    expense_id: str
    current_status: str  # "submitted", "processing", "under_review", "approved", "final_rejection", "rejected_with_instructions", "paid"
    processing_history: List[str]
    last_updated: datetime
    estimated_completion: Optional[datetime]


# Decision workflow results for internal orchestration
class ExpenseProcessingResult(BaseModel):
    """
    Complete processing result combining all agent outputs.
    """
    expense_report: ExpenseReport
    categorization: ExpenseCategory
    policy_evaluation: PolicyEvaluation
    fraud_assessment: FraudAssessment  # Internal only
    final_decision: FinalDecision
    expense_response: ExpenseResponse
    status: ExpenseStatus 