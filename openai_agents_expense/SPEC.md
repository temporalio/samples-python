# OpenAI Agents Expense Processing Sample

This sample extends the Temporal expense example with OpenAI Agents SDK to demonstrate AI-enhanced expense processing with robust guardrails and multi-agent orchestration.

**Purpose**: Show the benefits of combining Temporal's durable execution with the OpenAI Agents SDK for complex business workflows requiring AI decision-making, guardrails, and human-in-the-loop processing.

## Business Requirements

### Expense Processing Flow
1. **Expense Submission**: Employee submits expense report with required details
2. **AI Categorization**: Automatically categorize the expense using AI, using web search for vendor validation
3. **Policy & Fraud Analysis**: AI agents evaluate against departmental policies and fraud detection rules (using categorization results)
4. **Approval Decision**: AI makes approval recommendation, escalating to human review when needed (including mandatory escalations)
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
- **Receipt Requirements**: All expenses over $75 require receipt documentation (trust receipt_provided flag)
- **Late Submission**: Expenses older than 60 days require manager approval
- **Equipment Threshold**: Any equipment/hardware over $250 requires human approval
- **Client Entertainment**: Entertainment expenses require client name and business justification

#### Fraud Detection Patterns
- **Fake Vendors**: Detect suspicious or non-existent vendor names using web search validation
- **Unreasonable Amounts**: Flag amounts that don't make sense for the category/vendor
- **Vendor-Description Mismatch**: Identify mismatches between vendor and expense description
- **Duplicate Detection**: Identify potential duplicate submissions
- **Anomaly Detection**: Flag unusual patterns in spending behavior
- **Weekend/Holiday Restrictions**: Non-essential expenses on weekends/holidays flagged for review
- **Round Number Bias**: Flag suspiciously round amounts (fraudulent expenses often use exact dollar amounts like $100, $200)

#### Approval Logic
- **Automatic Approval**: Clear, policy-compliant expenses under certain thresholds with low fraud risk
- **Mandatory Human Review**: 
  - International travel (regardless of AI assessment)
  - Flight expenses over $500 (regardless of AI assessment)
  - Equipment/hardware over $250 (regardless of AI assessment)
  - Late submissions over 60 days (regardless of AI assessment)
- **AI-Determined Human Review**:
  - Low confidence in categorization, policy evaluation, or fraud assessment
  - Policy violations that may have exceptions
  - Medium to high fraud risk flags
  - Agent processing failures after retry attempts
- **Automatic Rejection**: Clear policy violations with no exceptions allowed and low fraud risk

## Technical Implementation

### Agent Architecture
Following a sequential multi-agent orchestration pattern with clear information boundaries:

#### 1. CategoryAgent (Public)
- **Purpose**: Automatically categorize expenses using AI and validate vendor information via web search
- **Web Search**: Searches for vendor information to validate legitimacy and gather business context
- **Output**: Structured `ExpenseCategory` with confidence score, reasoning, and `VendorValidation`
- **Information Access**: Public - safe to share categorization logic and vendor research with users
- **Dependencies**: None (processes raw expense data)

#### 2. PolicyEvaluationAgent (Public)
- **Purpose**: Evaluate expenses against departmental policies and business rules
- **Logic**: Apply transparent business rules and identify policy violations using expense data and categorization
- **Output**: Structured `PolicyEvaluation` with clear policy explanations and confidence score
- **Information Access**: Public - policy explanations are transparent to employees
- **Dependencies**: Requires `ExpenseCategory` results for policy application

#### 3. FraudAgent (Private)
- **Purpose**: Detect fraudulent or suspicious expense patterns using categorization context
- **Guardrails**: Strict output guardrails to prevent rule exfiltration
- **Web Search**: Can perform additional web searches if fraud patterns warrant deeper vendor investigation
- **Output**: Structured `FraudAssessment` with risk level, flags, and confidence score
- **Information Access**: Private - fraud detection methods must be protected
- **Dependencies**: Requires `ExpenseCategory` results for context-aware fraud detection

#### 4. DecisionOrchestrationAgent (Private)
- **Purpose**: Make final approval decisions using all available context, respecting mandatory escalation rules
- **Logic**: 
  - First checks for mandatory human review requirements (overrides AI assessment)
  - If no mandatory escalation, combines policy evaluation and fraud assessment 
  - Considers confidence scores from all agents
  - Decides: auto-approve, auto-reject, or escalate to human
- **Integration**: Seamlessly integrates with existing Temporal human-in-the-loop pattern
- **Output**: Structured `FinalDecision` with sanitized reasoning (no fraud details exposed)
- **Information Access**: Private - sees all context but only outputs sanitized decisions
- **Dependencies**: Requires `PolicyEvaluation` and `FraudAssessment` results

#### 5. ResponseAgent (Public)
- **Purpose**: Generate personalized responses to expense submitters
- **Input**: Final decision + sanitized reasoning + policy evaluation + categorization (fraud details excluded)
- **Output**: Human-friendly explanation of approval/rejection decision
- **Information Access**: Public - only sees final decisions, policy explanations, and categorization details
- **Dependencies**: Requires `FinalDecision`, `PolicyEvaluation`, and `ExpenseCategory` results

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
    receipt_provided: bool  # For receipt requirements over $75 (trust this flag)
    submission_date: date  # To detect late submissions (>60 days)
    client_name: Optional[str] = None  # Required for entertainment expenses
    business_justification: Optional[str] = None  # Required for client entertainment
    is_international_travel: bool = False  # Requires human approval regardless of amount

class VendorValidation(BaseModel):
    vendor_name: str
    is_legitimate: bool
    confidence_score: float
    web_search_summary: str  # Summary of web search findings (website, business description, etc.)
    # Note: risk_indicators moved to FraudAgent for security

class ExpenseCategory(BaseModel):
    category: str  # One of: "Travel & Transportation", "Meals & Entertainment", "Office Supplies", 
                  # "Software & Technology", "Marketing & Advertising", "Professional Services", 
                  # "Training & Education", "Equipment & Hardware", "Other"
    confidence: float
    reasoning: str  # Includes vendor validation details: website URLs, business description summary, 
                   # company information found via web search, and any public legitimacy concerns
    vendor_validation: VendorValidation

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
    mandatory_human_review: bool  # Based on mandatory escalation rules
    policy_explanation: str  # Clear explanation of applicable policies
    confidence: float

class FraudFlag(BaseModel):
    flag_type: str
    risk_level: str  # "low", "medium", "high"
    details: str  # Carefully sanitized to not reveal detection methods

class FraudAssessment(BaseModel):
    overall_risk: str  # "low", "medium", "high"
    flags: List[FraudFlag]
    reasoning: str  # Heavily guarded to not reveal detection methods
    requires_human_review: bool  # Based on fraud risk level
    confidence: float
    vendor_risk_indicators: List[str]  # Private risk indicators derived from analysis

class FinalDecision(BaseModel):
    decision: str  # "approved", "requires_human_review", "rejected"
    reasoning: str  # Sanitized - combines policy and risk without exposing fraud methods
    escalation_reason: Optional[str] = None  # Generic reason for human escalation
    is_mandatory_escalation: bool  # Whether escalation is due to mandatory rules
    confidence: float  # Overall confidence in the decision

class ExpenseResponse(BaseModel):
    message: str
    decision_summary: str
    policy_explanation: Optional[str]  # Clear policy explanations when relevant
    categorization_summary: str  # Summary of categorization and vendor validation
    next_steps: Optional[str]

class ExpenseStatus(BaseModel):
    expense_id: str
    current_status: str  # "submitted", "processing", "under_review", "approved", "rejected", "paid"
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
- **Web Search Safety**: Sanitize search queries to prevent malicious searches

**Output Guardrails:**
- **Category Consistency**: Ensure categorization aligns with the defined 9 categories
- **Reasoning Transparency**: Provide clear, explainable reasoning for categorization decisions
- **Confidence Scoring**: Include appropriate confidence levels for categorization
- **Vendor Information Transparency**: Share web search findings openly with users

#### PolicyEvaluationAgent Guardrails (Public)
**Input Guardrails:**
- **Categorization Dependency**: Validate that categorization results are available and valid
- **Business Rule Data Validation**: 
  - Validate international travel flag consistency with description/vendor
  - Ensure client name and justification are provided for entertainment expenses
  - Verify receipt documentation requirements alignment
  - Check submission date vs expense date for late submission detection

**Output Guardrails:**
- **Policy Transparency**: Clearly explain departmental policy requirements and thresholds to submitters
- **Complete Policy Communication**: Provide full context on policy violations including specific amounts and requirements
- **Professional Language**: Use clear, professional language for policy explanations
- **Educational Value**: Help employees understand policies to prevent future violations
- **Mandatory Escalation Identification**: Clearly identify when human review is mandatory vs optional

#### FraudAgent Guardrails (Private - Critical Security)
**Input Guardrails:**
- **Data Sanitization**: Prevent prompt injection that could reveal fraud detection methods
- **Context Isolation**: Ensure fraud detection operates independently while using categorization context
- **Web Search Protection**: If additional searches are performed, protect search methodology

**Output Guardrails (Critical):**
- **Rule Exfiltration Prevention**: Ensure fraud detection reasoning doesn't reveal specific detection methods or patterns
- **Detection Method Protection**: Never disclose internal fraud detection algorithms or triggers
- **Web Search Method Protection**: Don't expose additional search methodology or database specifics
- **Generic Risk Assessment**: Provide risk levels without exposing underlying detection logic
- **Pattern Protection**: Avoid revealing what patterns trigger fraud flags
- **Threshold Obfuscation**: Never reveal specific fraud detection thresholds or criteria

#### DecisionOrchestrationAgent Guardrails (Private)
**Input Guardrails:**
- **Context Integration**: Safely combine public policy evaluation with private fraud assessment
- **Decision Logic Protection**: Protect the decision-making algorithms that combine multiple inputs
- **Confidence Assessment**: Properly weight confidence scores from all agents in decision making

**Output Guardrails:**
- **Information Sanitization**: Remove all fraud detection details from decision reasoning
- **Policy Integration**: Include relevant policy explanations while excluding fraud context
- **Escalation Logic Protection**: Don't reveal what combinations of factors trigger human escalation
- **Confidence Reporting**: Provide appropriate overall confidence without exposing internal scoring methods
- **Mandatory Rule Transparency**: Clearly communicate when escalation is due to mandatory rules vs AI assessment

#### ResponseAgent Guardrails (Public)
**Input Guardrails:**
- **Fraud Detail Exclusion**: Only receive sanitized decisions and policy evaluations (no fraud assessment details)
- **Policy Context Access**: Full access to policy explanations for user education
- **Categorization Access**: Access to categorization and vendor validation for transparency

**Output Guardrails:**
- **Response Appropriateness**: Ensure all responses are professional and appropriate
- **Fraud Response Protection**: When fraud factors influenced the decision, provide only generic guidance without revealing why
- **Policy Education**: Clearly explain policy violations and requirements to help users improve
- **Escalation Communication**: Provide appropriate next steps for human review without revealing internal processes
- **Transparency Balance**: Share categorization and policy reasoning while protecting fraud detection methods

### Error Handling and Retry Logic
- **Agent Retry Policy**: If any agent fails, retry up to 3 times with exponential backoff
- **Escalation on Failure**: After 3 failed retry attempts, automatically escalate to human review
- **Explicit Escalation**: Agents can explicitly request human escalation if they encounter ambiguous situations
- **Confidence-Based Escalation**: Low confidence scores trigger human review:
  - **CategoryAgent**: Confidence < 0.7 triggers escalation
  - **PolicyEvaluationAgent**: Confidence < 0.8 triggers escalation  
  - **FraudAgent**: Confidence < 0.6 triggers escalation
  - **DecisionOrchestrationAgent**: Overall confidence < 0.75 triggers escalation
- **Graceful Degradation**: System continues processing with available agent results, escalating when critical agents fail

### Temporal Workflow Integration
- **ExpenseWorkflow**: Main workflow orchestrating all agents with enhanced AI decision-making
- **Sequential Processing**: CategoryAgent → [PolicyEvaluationAgent + FraudAgent] → DecisionOrchestrationAgent → ResponseAgent
- **Durable Execution**: All AI processing is durable and resumable
- **Human-in-the-Loop Enhancement**: AI-augmented decision-making that seamlessly escalates to human review when needed
- **Async Completion Integration**: When `DecisionOrchestrationAgent` determines human review is required, workflow uses existing async completion pattern
- **Status Updates**: Workflow updates `ExpenseStatus` at key milestones based on processing stage, not timing
- **Observability**: Full tracing of AI decision-making process (with appropriate redaction of sensitive information)
- **Error Handling**: Graceful handling of AI service failures with fallback to human review

### Information Flow Architecture
```
ExpenseSubmission (status: submitted)
  ↓
CategoryAgent processes raw expense data (status: processing)
  ↓
[PolicyEvaluationAgent + FraudAgent] - parallel processing using CategoryAgent results (status: processing)  
  ↓
DecisionOrchestrationAgent combines all agent results (status: processing)
  ↓
Decision: [Auto-Approve/Auto-Reject] OR [Human Review via Async Completion] 
  ↓ (if human review needed)
Status: under_review, workflow waits for async completion
  ↓ (after decision made)
ResponseAgent explains final decision (status: processing)
  ↓
Final Status: approved/rejected → (if approved) → paid
```

**Information Sharing Between Agents:**
- **PolicyEvaluationAgent** receives full `ExpenseCategory` object including categorization reasoning and vendor validation summary
- **FraudAgent** receives `ExpenseCategory` results through the reasoning field which includes:
  - Website URLs found during vendor validation
  - Summary of vendor's business description and legitimacy assessment  
  - Public information gathered from web search (company size, industry, location)
  - Categorization confidence and reasoning
  - Any public red flags (e.g., "website not found", "business description unclear")
- **DecisionOrchestrationAgent** receives complete results from PolicyEvaluationAgent and FraudAgent
- **ResponseAgent** receives sanitized decision and full policy/categorization context (fraud details excluded)

### Web Search Enhancement
- **CategoryAgent Web Search**: Searches for vendor information to validate legitimacy and gather business context (website, business description, etc.)
- **FraudAgent Additional Search**: Can perform targeted additional searches if fraud patterns warrant deeper investigation
- **Search Result Protection**: CategoryAgent search results are transparent; FraudAgent search methodology is protected
- **Data Enrichment**: Web search enhances both categorization accuracy and fraud detection capabilities

### Development Simplicity
- **Self-Contained**: No external systems beyond the UI (like original expense sample)
- **Simplified Business Rules**: Removed complex vendor databases and pre-approval systems for clarity
- **Clear Demonstrations**: Each agent showcases specific OpenAI Agents SDK capabilities
- **Extensible**: Easy to add new business rules or agent capabilities
- **Testable**: Clear separation of concerns for unit and integration testing
- **Information Boundary Testing**: Verify that fraud detection methods never leak across security boundaries

This sample demonstrates:
- Multi-agent orchestration with Temporal durability
- Robust guardrails for business-critical AI operations with clear information boundaries
- Web search integration for data enrichment and enhanced decision-making
- AI-augmented workflows with seamless human-in-the-loop integration
- Structured outputs and robust error handling
- Confidence-based decision making with appropriate escalation strategies