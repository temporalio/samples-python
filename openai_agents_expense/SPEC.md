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
Following the multi-agent orchestration pattern from the research workflow:

#### 1. CategoryAgent
- **Purpose**: Automatically categorize expenses using AI
- **Enhancement**: Uses web search to validate vendors and improve categorization accuracy
- **Output**: Structured `ExpenseCategory` with confidence score and reasoning

#### 2. PolicyAgent (Combined Policy + Approval)
- **Purpose**: Evaluate against departmental policies and make approval decisions
- **Logic**: Apply business rules and determine if human review is needed
- **Output**: Structured `ApprovalDecision` with policy compliance details

#### 3. FraudAgent
- **Purpose**: Detect fraudulent or suspicious expense patterns
- **Guardrails**: Strict output guardrails to prevent rule exfiltration
- **Enhancement**: Uses web search to validate vendor information
- **Output**: Structured `FraudAssessment` with risk level and flags

#### 4. ResponseAgent
- **Purpose**: Generate personalized responses to expense submitters
- **Input**: Expense details + all agent assessments (with fraud details redacted)
- **Output**: Human-friendly explanation of approval/rejection decision
- **Fraud Protection**: When fraud flags are present, provides generic "please contact your manager" response without revealing detection methods

### Pydantic Data Models

```python
class ExpenseReport(BaseModel):
    expense_id: str
    amount: Decimal
    description: str
    vendor: str
    date: date
    department: str
    employee_id: str

class ExpenseCategory(BaseModel):
    category: str  # One of the 9 categories
    confidence: float
    reasoning: str

class PolicyViolation(BaseModel):
    rule_name: str
    violation_type: str
    severity: str  # "warning", "requires_review", "rejection"
    details: str

class ApprovalDecision(BaseModel):
    decision: str  # "approved", "requires_review", "rejected"
    policy_violations: List[PolicyViolation]
    reasoning: str
    requires_human_review: bool

class FraudFlag(BaseModel):
    flag_type: str
    risk_level: str  # "low", "medium", "high"
    details: str

class FraudAssessment(BaseModel):
    overall_risk: str  # "low", "medium", "high"
    flags: List[FraudFlag]
    reasoning: str  # Carefully guarded to not reveal detection methods

class ExpenseResponse(BaseModel):
    message: str
    decision_summary: str
    next_steps: Optional[str]
```

### Guardrails Implementation

#### Input Guardrails
- **Expense Validation**: Ensure submitted data contains valid expense information
- **Field Sanitization**: Prevent prompt injection via description, vendor, or other text fields
- **Data Type Validation**: Verify amounts, dates, and IDs are properly formatted

#### Output Guardrails (Critical for FraudAgent)
- **Rule Exfiltration Prevention**: Ensure fraud detection reasoning doesn't reveal specific detection methods
- **Sensitive Information Protection**: Prevent disclosure of internal policies or fraud patterns
- **Response Appropriateness**: Ensure all responses are professional and appropriate
- **Fraud Response Protection**: When fraud is detected, ResponseAgent provides only generic guidance ("please contact your manager") without exposing fraud assessment details

### Temporal Workflow Integration
- **ExpenseWorkflow**: Main workflow orchestrating all agents (replaces human approval step)
- **Durable Execution**: All AI processing is durable and resumable
- **Human-in-the-Loop**: When human review is required, workflow waits asynchronously
- **Observability**: Full tracing of AI decision-making process
- **Error Handling**: Graceful handling of AI service failures

### Web Search Enhancement
Following the search agent pattern:
- **Vendor Validation**: Search for vendor information to validate legitimacy
- **Category Enhancement**: Use search results to improve expense categorization
- **Fraud Detection**: Cross-reference vendor details against known databases

### Development Simplicity
- **Self-Contained**: No external systems beyond the UI (like original expense sample)
- **Clear Demonstrations**: Each agent showcases specific OpenAI Agents SDK capabilities
- **Extensible**: Easy to add new business rules or agent capabilities
- **Testable**: Clear separation of concerns for unit and integration testing

This sample demonstrates:
- Multi-agent orchestration with Temporal durability
- Sophisticated guardrails for sensitive AI operations
- Web search integration for enhanced decision-making
- Human-in-the-loop workflows with AI augmentation
- Structured outputs and robust error handling