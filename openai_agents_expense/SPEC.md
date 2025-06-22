# OpenAI Agents Expense Processing Sample

This sample extends the Temporal expense example with OpenAI Agents SDK to demonstrate AI-enhanced expense processing with robust guardrails and multi-agent orchestration.

**Purpose**: Show the benefits of combining Temporal's durable execution with the OpenAI Agents SDK for complex business workflows requiring AI decision-making, guardrails, and human-in-the-loop processing.

## Business Requirements

### Expense Processing Flow
1. **Expense Submission**: Employee submits expense report with required details
2. **AI Categorization**: Automatically categorize the expense using AI, using web search when necessary
3. **Policy & Fraud Analysis**: AI agents evaluate against departmental policies and fraud detection rules
4. **Approval Decision**: AI makes approval recommendation, escalating to human review when needed
5. **Response Generation**: AI generates personalized response to submitter explaining the decision
6. **Payment Processing**: If approved, process the payment (same as original sample)
7. **Status Tracking**: Employees can check the current status and processing history of their expense submissions

### Expense Data Model
Each expense report contains:
- **expense_id**: Unique identifier
- **amount**: Dollar amount (decimal)
- **description**: What the expense was for
- **vendor**: Who was paid
- **date**: When the expense occurred
- **department**: Submitting department
- **employee_id**: Employee identifier

### Expense Categories (8 + Other)
1. Travel & Transportation
2. Meals & Entertainment
3. Office Supplies
4. Software & Technology
5. Marketing & Advertising
6. Professional Services
7. Training & Education
8. Equipment & Hardware
9. Other

### Business Rules

#### Departmental Policies
- **Flight Limit**: No flights more than $500 without human approval
- **International Travel**: All international travel requires human approval regardless of amount
- **Personal Shopping**: No personal shopping expenses allowed
- **Category Limits**: Each department may have category-specific spending limits
- **Receipt Requirements**: All expenses over $75 require receipt documentation
- **Late Submission**: Expenses older than 60 days require manager approval
- **Equipment Threshold**: Any equipment/hardware over $250 requires IT department pre-approval
- **Client Entertainment**: Entertainment expenses require client name and business justification
- **Vendor Pre-Approval**: New vendors over $500 must be in approved vendor database

#### Fraud Detection Patterns
- **Fake Vendors**: Detect suspicious or non-existent vendor names
- **Unreasonable Amounts**: Flag amounts that don't make sense for the category/vendor
- **Vendor-Description Mismatch**: Identify mismatches between vendor and expense description
- **Duplicate Detection**: Identify potential duplicate submissions
- **Anomaly Detection**: Flag unusual patterns in spending behavior
- **Weekend/Holiday Restrictions**: Non-essential expenses on weekends/holidays flagged for review
- **Round Number Bias**: Flag suspiciously round amounts (fraudulent expenses often use exact dollar amounts like $100, $200)

#### Approval Logic
- **Automatic Approval**: Clear, policy-compliant expenses under certain thresholds
- **Human Review Required**: 
  - Policy violations that may have exceptions
  - Fraud detection flags requiring investigation
  - High-value expenses requiring managerial oversight
- **Automatic Rejection**: Clear policy violations with no exceptions allowed

## Technical Implementation

### Agent Architecture
Following a hierarchical multi-agent orchestration pattern with clear information boundaries:

#### 1. CategoryAgent (Public)
- **Purpose**: Automatically categorize expenses using AI
- **Enhancement**: Uses web search to validate vendors and improve categorization accuracy  
- **Output**: Structured `ExpenseCategory` with confidence score and reasoning
- **Information Access**: Public - safe to share categorization logic with users


#### 2. PolicyEvaluationAgent (Public)
- **Purpose**: Evaluate expenses against departmental policies and business rules
- **Logic**: Apply transparent business rules and identify policy violations
- **Output**: Structured `PolicyEvaluation` with clear policy explanations
- **Information Access**: Public - policy explanations are transparent to employees

#### 3. FraudAgent (Private)
- **Purpose**: Detect fraudulent or suspicious expense patterns
- **Guardrails**: Strict output guardrails to prevent rule exfiltration
- **Enhancement**: Uses web search to validate vendor information
- **Output**: Structured `FraudAssessment` with risk level and flags
- **Information Access**: Private - fraud detection methods must be protected

#### 4. DecisionOrchestrationAgent (Private)
- **Purpose**: Make final approval decisions using all available context
- **Logic**: Combines policy evaluation and fraud assessment to decide: auto-approve, auto-reject, or escalate to human
- **Integration**: Seamlessly integrates with existing Temporal human-in-the-loop pattern
- **Output**: Structured `FinalDecision` with sanitized reasoning (no fraud details exposed)
- **Information Access**: Private - sees all context but only outputs sanitized decisions

#### 5. ResponseAgent (Public)
- **Purpose**: Generate personalized responses to expense submitters
- **Input**: Final decision + sanitized reasoning + policy evaluation (fraud details excluded)
- **Output**: Human-friendly explanation of approval/rejection decision
- **Information Access**: Public - only sees final decisions and policy explanations

### Pydantic Data Models

```python
class ExpenseReport(BaseModel):
    expense_id: str
    amount: Decimal
    description: str
    vendor: str
    date: date  # When the expense occurred
    department: str
    employee_id: str
    # Enhanced fields for business rule support
    receipt_provided: bool  # For receipt requirements over $75
    submission_date: date  # To detect late submissions (>60 days)
    client_name: Optional[str] = None  # Required for entertainment expenses
    business_justification: Optional[str] = None  # Required for client entertainment
    is_international_travel: bool = False  # Requires human approval regardless of amount
    it_pre_approved: bool = False  # Required for equipment/hardware over $250
    vendor_pre_approved: bool = False  # Required for new vendors over $500

class ExpenseCategory(BaseModel):
    category: str  # One of: "Travel & Transportation", "Meals & Entertainment", "Office Supplies", 
                  # "Software & Technology", "Marketing & Advertising", "Professional Services", 
                  # "Training & Education", "Equipment & Hardware", "Other"
    confidence: float
    reasoning: str

class PolicyViolation(BaseModel):
    rule_name: str
    violation_type: str
    severity: str  # "warning", "requires_review", "rejection"
    details: str
    threshold_amount: Optional[Decimal] = None  # For dollar-based thresholds

class PolicyEvaluation(BaseModel):
    compliant: bool
    violations: List[PolicyViolation]
    reasoning: str
    requires_human_review: bool  # Based on policy complexity, not fraud
    policy_explanation: str  # Clear explanation of applicable policies

class FraudFlag(BaseModel):
    flag_type: str
    risk_level: str  # "low", "medium", "high"
    details: str  # Carefully sanitized to not reveal detection methods

class FraudAssessment(BaseModel):
    overall_risk: str  # "low", "medium", "high"
    flags: List[FraudFlag]
    reasoning: str  # Heavily guarded to not reveal detection methods
    requires_human_review: bool  # Based on fraud risk level

class FinalDecision(BaseModel):
    decision: str  # "approved", "requires_human_review", "rejected"
    reasoning: str  # Sanitized - combines policy and risk without exposing fraud methods
    escalation_reason: Optional[str] = None  # Generic reason for human escalation
    decision_confidence: float  # AI confidence in the decision

class VendorValidation(BaseModel):
    vendor_name: str
    is_legitimate: bool
    confidence_score: float
    search_results_summary: str
    risk_indicators: List[str]

class DepartmentPolicy(BaseModel):
    department: str
    category_limits: Dict[str, Decimal]  # Category-specific spending limits
    special_rules: List[str]  # Department-specific business rules

class ExpenseResponse(BaseModel):
    message: str
    decision_summary: str
    policy_explanation: Optional[str]  # Clear policy explanations when relevant
    next_steps: Optional[str]

class ExpenseStatus(BaseModel):
    expense_id: str
    current_status: str  # "submitted", "categorizing", "policy_review", "fraud_review", 
                        # "human_review", "approved", "rejected", "paid"
    processing_history: List[str]
    last_updated: datetime
    estimated_completion: Optional[datetime]
```

### Guardrails Implementation

The guardrails are organized by agent to provide clear security boundaries between transparent business operations and protected fraud detection mechanisms.

#### CategoryAgent Guardrails (Public)
**Input Guardrails:**
- **Expense Validation**: Ensure expense data contains valid vendor and description information
- **Field Sanitization**: Prevent prompt injection via description or vendor fields
- **Data Type Validation**: Verify amounts and dates are properly formatted

**Output Guardrails:**
- **Category Consistency**: Ensure categorization aligns with the defined 9 categories
- **Reasoning Transparency**: Provide clear, explainable reasoning for categorization decisions
- **Confidence Scoring**: Include appropriate confidence levels for categorization

#### PolicyEvaluationAgent Guardrails (Public)
**Input Guardrails:**
- **Business Rule Data Validation**: 
  - Validate international travel flag consistency with description/vendor
  - Ensure client name and justification are provided for entertainment expenses
  - Verify receipt documentation requirements alignment
  - Validate IT and vendor pre-approval status consistency
  - Check submission date vs expense date for late submission detection

**Output Guardrails:**
- **Policy Transparency**: Clearly explain departmental policy requirements and thresholds to submitters
- **Complete Policy Communication**: Provide full context on policy violations including specific amounts and requirements
- **Professional Language**: Use clear, professional language for policy explanations
- **Educational Value**: Help employees understand policies to prevent future violations

#### FraudAgent Guardrails (Private - Critical Security)
**Input Guardrails:**
- **Data Sanitization**: Prevent prompt injection that could reveal fraud detection methods
- **Context Isolation**: Ensure fraud detection operates independently of policy evaluation

**Output Guardrails (Critical):**
- **Rule Exfiltration Prevention**: Ensure fraud detection reasoning doesn't reveal specific detection methods or patterns
- **Detection Method Protection**: Never disclose internal fraud detection algorithms or triggers
- **Vendor Validation Protection**: Don't expose search methodology or vendor database specifics
- **Generic Risk Assessment**: Provide risk levels without exposing underlying detection logic
- **Pattern Protection**: Avoid revealing what patterns trigger fraud flags
- **Threshold Obfuscation**: Never reveal specific fraud detection thresholds or criteria

#### DecisionOrchestrationAgent Guardrails (Private)
**Input Guardrails:**
- **Context Integration**: Safely combine public policy evaluation with private fraud assessment
- **Decision Logic Protection**: Protect the decision-making algorithms that combine multiple inputs

**Output Guardrails:**
- **Information Sanitization**: Remove all fraud detection details from decision reasoning
- **Policy Integration**: Include relevant policy explanations while excluding fraud context
- **Escalation Logic Protection**: Don't reveal what combinations of factors trigger human escalation
- **Decision Confidence**: Provide appropriate confidence without exposing internal scoring methods

#### ResponseAgent Guardrails (Public)
**Input Guardrails:**
- **Fraud Detail Exclusion**: Only receive sanitized decisions and policy evaluations (no fraud assessment details)
- **Policy Context Access**: Full access to policy explanations for user education

**Output Guardrails:**
- **Response Appropriateness**: Ensure all responses are professional and appropriate
- **Fraud Response Protection**: When fraud factors influenced the decision, provide only generic guidance without revealing why
- **Policy Education**: Clearly explain policy violations and requirements to help users improve
- **Escalation Communication**: Provide appropriate next steps for human review without revealing internal processes

### Temporal Workflow Integration
- **ExpenseWorkflow**: Main workflow orchestrating all agents with enhanced AI decision-making
- **Durable Execution**: All AI processing is durable and resumable
- **Human-in-the-Loop Enhancement**: AI-augmented decision-making that seamlessly escalates to human review when needed
- **Async Completion Integration**: When `DecisionOrchestrationAgent` determines human review is required, workflow uses existing async completion pattern
- **Observability**: Full tracing of AI decision-making process (with appropriate redaction of sensitive information)
- **Error Handling**: Graceful handling of AI service failures with fallback to human review

### Information Flow Architecture
```
ExpenseSubmission
  ↓
CategoryAgent (public) 
  ↓
[PolicyEvaluationAgent (public) + FraudAgent (private)] - parallel processing
  ↓
DecisionOrchestrationAgent (private - sees all context)
  ↓
Decision: [Auto-Approve/Auto-Reject] OR [Human Review via Async Completion]
  ↓
ResponseAgent (public - explains final decision using policy context only)
```

### Web Search Enhancement
Following the search agent pattern:
- **Vendor Validation**: Search for vendor information to validate legitimacy
- **Category Enhancement**: Use search results to improve expense categorization
- **Data Enrichment**: Cross-reference vendor details and enhance expense context with external information
- **Fraud Detection**: Cross-reference vendor details against known databases (results protected by FraudAgent guardrails)

### Development Simplicity
- **Self-Contained**: No external systems beyond the UI (like original expense sample)
- **Clear Demonstrations**: Each agent showcases specific OpenAI Agents SDK capabilities
- **Extensible**: Easy to add new business rules or agent capabilities
- **Testable**: Clear separation of concerns for unit and integration testing
- **Information Boundary Testing**: Verify that sensitive information never leaks across security boundaries

This sample demonstrates:
- Multi-agent orchestration with Temporal durability
- Robust guardrails for business-critical AI operations with clear information boundaries
- Web search integration for data enrichment and enhanced decision-making
- AI-augmented workflows with seamless human-in-the-loop integration
- Structured outputs and robust error handling