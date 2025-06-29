"""
Pydantic data models for the OpenAI Agents Expense Processing Sample.

These models define the structured data types used throughout the expense processing workflow,
including expense reports, agent outputs, and decision results.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

# Valid expense status values
ExpenseStatusType = Literal[
    "uninitialized",
    "submitted",
    "processing",
    "manager_review",
    "approved",
    "final_rejection",
    "rejected_with_instructions",
    "paid",
]


class ExpenseReport(BaseModel):
    """
    Core expense report data submitted by employees.
    """

    expense_id: str = Field(
        description="Unique identifier for the expense report", min_length=1
    )
    amount: Decimal = Field(description="Expense amount in USD", gt=0, decimal_places=2)
    description: str = Field(
        description="Description of the expense", min_length=1, max_length=500
    )
    vendor: str = Field(
        description="Vendor or merchant name", min_length=1, max_length=200
    )
    expense_date: date = Field(description="Date when the expense occurred")
    department: str = Field(
        description="Employee's department", min_length=1, max_length=100
    )
    employee_id: str = Field(description="Employee identifier", min_length=1)
    receipt_provided: bool = Field(
        description="Whether a receipt was provided (required for expenses over $75)"
    )
    submission_date: date = Field(
        description="Date when the expense was submitted (used to detect late submissions over 60 days)"
    )
    client_name: Optional[str] = Field(
        default=None,
        description="Client name (required for entertainment expenses)",
        max_length=200,
    )
    business_justification: Optional[str] = Field(
        default=None,
        description="Business justification (required for entertainment expenses)",
        max_length=1000,
    )
    is_international_travel: bool = Field(
        default=False,
        description="Whether this expense is related to international travel (requires human approval regardless of amount)",
    )


class VendorValidation(BaseModel):
    """
    Results of vendor validation through web search.
    """

    vendor_name: str = Field(
        description="Name of the vendor being validated", min_length=1, max_length=200
    )
    is_legitimate: bool = Field(
        description="Whether the vendor appears to be legitimate"
    )
    confidence_score: float = Field(
        description="Confidence score for the validation result", ge=0.0, le=1.0
    )
    web_search_summary: str = Field(
        description="Summary of web search findings: website URLs, business description, company information, search result quality (clear/conflicting/missing/insufficient), and any public legitimacy concerns or verification details",
        min_length=1,
    )


class ExpenseCategory(BaseModel):
    """
    Categorization results from CategoryAgent.
    """

    category: str = Field(
        description="Expense category (e.g., Travel & Transportation, Meals & Entertainment, Office Supplies, Software & Technology, Marketing & Advertising, Professional Services, Training & Education, Equipment & Hardware, Other)",
        min_length=1,
        max_length=100,
    )
    confidence: float = Field(
        description="Confidence score for the categorization", ge=0.0, le=1.0
    )
    reasoning: str = Field(
        description="Reasoning for the categorization, includes vendor validation details: website URLs, business description summary, company information found via web search, and any public legitimacy concerns",
        min_length=1,
    )
    vendor_validation: VendorValidation = Field(
        description="Vendor validation results from web search"
    )


class PolicyViolation(BaseModel):
    """
    Individual policy violation details.
    """

    rule_name: str = Field(
        description="Name of the policy rule that was violated",
        min_length=1,
        max_length=100,
    )
    violation_type: str = Field(
        description="Type of violation (e.g., 'policy_violation', 'documentation_missing', 'threshold_exceeded', 'information_missing', 'mandatory_review')",
        min_length=1,
        max_length=50,
    )
    severity: Literal["warning", "requires_review", "rejection"] = Field(
        description="Severity level of the violation"
    )
    details: str = Field(
        description="Detailed explanation of the violation",
        min_length=1,
        max_length=1000,
    )
    threshold_amount: Optional[Decimal] = Field(
        default=None,
        description="Dollar threshold associated with this violation, if applicable (use null for non-applicable)",
        gt=0,
        decimal_places=2,
    )

    @field_validator("threshold_amount", mode="before")
    @classmethod
    def validate_threshold_amount(cls, v):
        if v == "N/A" or v == "":
            return None
        return v


class PolicyEvaluation(BaseModel):
    """
    Policy evaluation results from PolicyEvaluationAgent.
    """

    compliant: bool = Field(
        description="Whether the expense is compliant with all policies",
    )
    violations: List[PolicyViolation] = Field(
        description="List of policy violations found, empty if compliant",
        default_factory=list,
    )
    reasoning: str = Field(
        description="Detailed reasoning for the policy evaluation decision",
        min_length=1,
        max_length=2000,
    )
    requires_human_review: bool = Field(
        description="Whether human review is required based on escalation rules or policy complexity(not fraud)",
    )
    policy_explanation: str = Field(
        description="Clear explanation of applicable policies and their requirements",
        min_length=1,
        max_length=1500,
    )
    confidence: float = Field(
        description="Confidence score for the policy evaluation",
        ge=0.0,
        le=1.0,
    )


class FraudFlag(BaseModel):
    """
    Individual fraud detection flag.
    """

    flag_type: str = Field(
        description="Type of fraud flag (e.g., 'duplicate_expense', 'suspicious_vendor', 'unusual_pattern')",
        min_length=1,
        max_length=50,
    )
    risk_level: Literal["low", "medium", "high"] = Field(
        description="Risk level associated with this flag",
    )
    details: str = Field(
        description="Sanitized details about the flag, carefully avoiding exposure of detection methods",
        min_length=1,
        max_length=500,
    )


class FraudAssessment(BaseModel):
    """
    Fraud assessment results from FraudAgent (Private - security critical).
    """

    overall_risk: Literal["low", "medium", "high"] = Field(
        description="Overall fraud risk assessment"
    )
    flags: List[FraudFlag] = Field(
        description="List of fraud flags identified, empty if no flags",
        default_factory=list,
    )
    reasoning: str = Field(
        description="Internal reasoning for fraud assessment (heavily guarded to protect detection methods)",
        min_length=1,
        max_length=2000,
    )
    requires_human_review: bool = Field(
        description="Whether human review is required based on fraud risk level",
    )
    confidence: float = Field(
        description="Confidence score for the fraud assessment",
        ge=0.0,
        le=1.0,
    )
    vendor_risk_indicators: List[str] = Field(
        description="Private risk indicators derived from vendor analysis",
        default_factory=list,
    )


class AgentDecision(BaseModel):
    """
    Final decision from DecisionOrchestrationAgent.
    """

    decision: Literal[
        "approved",
        "requires_human_review",
        "final_rejection",
        "rejected_with_instructions",
    ] = Field(description="Final decision on the expense")
    internal_reasoning: str = Field(
        description="Detailed reasoning for administrators, includes fraud context",
        min_length=1,
        max_length=3000,
    )
    external_reasoning: str = Field(
        description="Sanitized reasoning for users, no fraud details exposed",
        min_length=1,
        max_length=1500,
    )
    escalation_reason: Optional[str] = Field(
        default=None,
        description="Generic reason for human escalation",
        max_length=500,
    )
    is_mandatory_escalation: bool = Field(
        description="Whether escalation is due to mandatory rules",
    )
    confidence: float = Field(
        description="Overall confidence in the decision",
        ge=0.0,
        le=1.0,
    )


class ExpenseResponse(BaseModel):
    """
    Final response message from ResponseAgent.
    """

    decision_summary: str = Field(
        description="Summary of the decision including any resubmission instructions when applicable",
        min_length=1,
        max_length=1000,
    )
    policy_explanation: Optional[str] = Field(
        default=None,
        description="Clear policy explanations when relevant to the decision",
        max_length=1500,
    )
    categorization_summary: str = Field(
        description="Summary of expense categorization and vendor validation results",
        min_length=1,
        max_length=800,
    )


class ExpenseStatus(BaseModel):
    """
    Current status of expense processing.
    """

    current_status: ExpenseStatusType
    last_updated: datetime


# Decision workflow results for internal orchestration
class ExpenseProcessingData(BaseModel):
    """
    Complete processing result combining all agent outputs.
    """

    expense_status: ExpenseStatusType = "uninitialized"
    expense_report: Optional[ExpenseReport] = None
    categorization: Optional[ExpenseCategory] = None
    policy_evaluation: Optional[PolicyEvaluation] = None
    fraud_assessment: Optional[FraudAssessment] = None  # Internal only
    agent_decision: Optional[AgentDecision] = None
    expense_response: Optional[ExpenseResponse] = None

    def update(self, **kwargs):
        """Update the processing result with new data."""
        for key, value in kwargs.items():
            setattr(self, key, value)


# Activity input models
class PolicyEvaluationInput(BaseModel):
    """Input for policy evaluation activity."""

    expense_report: ExpenseReport
    categorization: ExpenseCategory


class FraudAssessmentInput(BaseModel):
    """Input for fraud assessment activity."""

    expense_report: ExpenseReport
    categorization: ExpenseCategory


class AgentDecisionInput(BaseModel):
    """Input for final decision activity."""

    expense_report: ExpenseReport
    categorization: ExpenseCategory
    policy_evaluation: PolicyEvaluation
    fraud_assessment: FraudAssessment


class ExpenseResponseInput(BaseModel):
    """Input for expense response generation activity."""

    expense_report: ExpenseReport
    categorization: ExpenseCategory
    policy_evaluation: PolicyEvaluation
    agent_decision: AgentDecision
    final_decision: ExpenseStatusType


class UpdateExpenseActivityInput(BaseModel):
    expense_id: str
    expense_processing_result: ExpenseProcessingData
