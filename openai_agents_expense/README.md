# OpenAI Agents Expense Processing Sample

This sample extends the Temporal expense example with **OpenAI Agents SDK** to demonstrate AI-enhanced expense processing with robust guardrails and multi-agent orchestration.

**Purpose**: Show the benefits of combining Temporal's durable execution with the OpenAI Agents SDK for complex business workflows requiring AI decision-making, guardrails, and human-in-the-loop processing.

## Overview

This sample demonstrates an AI-enhanced expense processing workflow with:

- **Multi-Agent Architecture**: Five specialized AI agents working in sequence
- **Robust Guardrails**: Security boundaries and fraud detection method protection  
- **Web Search Integration**: External data enrichment for vendor validation
- **Human-in-the-Loop**: Seamless escalation to human review when needed
- **Confidence Framework**: Systematic confidence thresholds for quality assurance

## Architecture

### Agent Flow
```
ExpenseSubmission
  ↓
CategoryAgent (Public)
  ↓
[PolicyEvaluationAgent (Public) + FraudAgent (Private)] - parallel
  ↓
DecisionOrchestrationAgent (Private)
  ↓
Decision Branch:
├─ Auto-Approve → ResponseAgent → Payment
├─ Final Rejection → ResponseAgent
├─ Rejection with Instructions → ResponseAgent  
└─ Human Review → Async Completion → ResponseAgent
```

### The Five AI Agents

#### 1. **CategoryAgent** (Public)
- **Purpose**: Categorize expenses and validate vendors via web search
- **Categories**: 9 predefined categories (Travel, Meals, Office Supplies, etc.)
- **Web Search**: Validates vendor legitimacy and gathers business context
- **Information Access**: Public - transparent vendor research shared with users

#### 2. **PolicyEvaluationAgent** (Public)  
- **Purpose**: Evaluate expenses against departmental policies
- **Policies**: Flight limits, international travel, receipt requirements, etc.
- **Mandatory Escalation**: Identifies rules that override AI assessment
- **Information Access**: Public - policy explanations transparent to employees

#### 3. **FraudAgent** (Private - Critical Security)
- **Purpose**: Detect fraudulent patterns with strict output guardrails
- **Security**: Protects fraud detection methods from information leakage
- **Context-Aware**: Uses categorization results for enhanced detection
- **Information Access**: Private - fraud methods must be protected

#### 4. **DecisionOrchestrationAgent** (Private)
- **Purpose**: Make final decisions combining all agent inputs
- **Decision Types**: Approved, Final Rejection, Human Review, Reject with Instructions
- **Confidence Framework**: Applies systematic thresholds for escalation
- **Information Access**: Private - sees all context, outputs sanitized decisions

#### 5. **ResponseAgent** (Public)
- **Purpose**: Generate personalized user responses
- **Tone**: Professional, educational, supportive based on decision type
- **Information Access**: Public - only sees sanitized decisions and policy explanations

## Key Features

### Business Rules
- **Flight Limit**: >$500 requires human approval
- **International Travel**: Always requires human approval
- **Personal Shopping**: Prohibited (automatic rejection)
- **Receipt Requirements**: >$75 requires receipt documentation
- **Late Submission**: >60 days requires manager approval
- **Equipment Threshold**: >$250 requires human approval
- **Client Entertainment**: Requires client name and business justification

### Security Guardrails
- **Information Boundaries**: Fraud detection methods never exposed to users
- **Output Sanitization**: Multiple layers of content validation
- **Prompt Injection Protection**: Input sanitization and manipulation detection
- **Role Confusion Detection**: Authority impersonation prevention

### Confidence Framework
Systematic thresholds trigger human escalation:
- **CategoryAgent**: < 0.70 (foundational errors cascade)
- **PolicyEvaluationAgent**: < 0.80 (deterministic evaluation)
- **FraudAgent**: < 0.65 (safety-critical, err on caution)
- **DecisionOrchestrationAgent**: < 0.75 (high-stakes decisions)

## Prerequisites

- Temporal server [running locally](https://docs.temporal.io/cli/server#start-dev)
- Required dependencies: `uv sync --group openai-agents --group expense` or `pip install -e ".[openai-agents,expense]"`
- OpenAI API key: `export OPENAI_API_KEY=your_key_here`

## Running the Sample

**Note**: This example is now **self-contained** and includes all necessary components from the basic expense example.

### 1. Start the Expense UI (for human review)
```bash
# Self-contained UI included in this example
uv run -m openai_agents_expense.ui
```

### 2. Start the Worker
```bash
uv run -m openai_agents_expense.worker
```

### 3. Start Expense Processing
```bash
uv run -m openai_agents_expense.starter
```

The starter provides three sample expenses:
1. **Happy Path**: Office supplies ($45) - should auto-approve
2. **International Travel**: Flight to London ($400) - mandatory escalation  
3. **Suspicious Vendor**: Dinner at suspicious restaurant ($200) - fraud escalation

### 4. Monitor Progress
- **Temporal Web UI**: http://localhost:8233
- **Expense Review UI**: http://localhost:8099/list (for human review)

## Test Scenarios

The sample includes 10 comprehensive test scenarios in the `/scenarios` directory:

1. **Happy Path Auto-Approval** - End-to-end positive workflow
2. **Prompt Injection Attack** - Security guardrail validation
3. **Suspicious Vendor Fraud Detection** - Information boundary protection
4. **Low Confidence Categorization** - Confidence-based escalation
5. **International Travel Mandatory Escalation** - Business rule enforcement
6. **Conflicting Vendor Information** - Fixable issue resolution
7. **Information Extraction Attempt** - Critical security testing
8. **Personal Shopping Final Rejection** - Policy enforcement
9. **Business Type Categorization Enhancement** - Web search benefits
10. **Role Confusion Guardrail** - Authority impersonation detection

Each scenario includes:
- Complete test data (JSON inputs)
- Expected outputs for all agents
- Unit test assertions
- Integration test validations
- LLM-as-Judge evaluation criteria

## Key Concepts Demonstrated

### Temporal + OpenAI Agents Integration
- **Durable AI Workflows**: AI agent processing with Temporal's reliability
- **Agent Orchestration**: Sequential and parallel agent coordination
- **Error Handling**: Graceful degradation and retry logic
- **State Management**: Persistent workflow state across agent calls

### Security & Guardrails
- **Information Boundaries**: Public vs. private agent access controls
- **Output Sanitization**: Multi-layer content validation
- **Fraud Method Protection**: Critical security for detection algorithms
- **Professional Communication**: Consistent appropriate tone

### Business Integration
- **Human-in-the-Loop**: Seamless escalation to human review
- **Policy Transparency**: Educational explanations for employees
- **Confidence-Based Quality**: Systematic thresholds for reliability
- **Decision Auditability**: Complete processing history and reasoning

## Self-Contained Architecture

**This example is completely self-contained** and does not depend on external examples. The following components were copied and adapted from the basic `expense` example to make this standalone:

- ✅ **Web UI** (`ui.py`) - Complete expense management interface
- ✅ **Basic Activities** (`activities/expense_activities.py`) - Core expense processing activities  
- ✅ **All Dependencies** - Uses existing `expense` dependency group from pyproject.toml

## File Structure

```
openai_agents_expense/
├── models.py                     # Pydantic data models
├── worker.py                     # Temporal worker
├── starter.py                    # Workflow starter
├── ui.py                         # Self-contained expense management UI
├── README.md                     # This file
├── SETUP.md                      # Detailed setup guide
├── ai_agents/                    # AI agent implementations
│   ├── category_agent.py
│   ├── policy_evaluation_agent.py
│   ├── fraud_agent.py
│   ├── decision_orchestration_agent.py
│   └── response_agent.py
├── activities/                   # Temporal activities
│   ├── web_search.py             # Web search for vendor validation
│   └── expense_activities.py     # Basic expense processing activities
├── workflows/                    # Temporal workflows
│   └── expense_workflow.py
└── scenarios/                    # Test scenarios
    ├── README.md
    ├── 01_happy_path_auto_approval.md
    ├── 02_prompt_injection_attack.md
    └── ... (8 more scenarios)
```

## Development and Testing

### Automated Test Suite

The sample includes comprehensive automated tests with mocked OpenAI responses:

```bash
# Run all basic tests (works on Python 3.9+)
python tests/test_models.py

# Run with pytest for detailed output  
python -m pytest tests/test_models.py -v

# Using the test runner script
python run_tests.py --type unit --verbose
```

**Test Coverage** (15 tests):
- ✅ Data model validation (ExpenseReport, PolicyEvaluation, FraudAssessment, etc.)
- ✅ Web search activity mocking with realistic vendor responses
- ✅ Business rule validation (receipt requirements, confidence thresholds)
- ✅ Expense categorization with all 9 supported categories
- ✅ Date calculations for late submission detection

See `tests/README.md` for detailed testing documentation and `tests/test_summary.md` for current test status.

### Running Individual Test Scenarios
Use the scenario files in `/scenarios` to:
- Create unit tests for individual agents
- Build integration tests for workflow orchestration  
- Implement LLM-as-judge evaluation
- Validate security boundary protection

### Adding New Business Rules
1. Update `PolicyEvaluationAgent` instructions
2. Add new validation logic in `evaluate_policy_compliance`
3. Update confidence thresholds if needed
4. Create test scenarios for the new rules

### Extending Fraud Detection
1. **Never expose detection methods** in agent instructions
2. Add new patterns to `FraudAgent` (internal only)
3. Update output sanitization in `_validate_security_compliance`
4. Test information boundary protection

## Troubleshooting

### Common Issues

**OpenAI API Errors**:
- Ensure `OPENAI_API_KEY` environment variable is set
- Check API rate limits and billing

**Agent JSON Parsing Errors**:
- Agents include fallback logic for parsing failures
- Check logs for specific JSON format issues

**Human Review Workflow**:
- Ensure the expense UI is running on port 8099
- Use the same expense IDs for integration

**Security Boundary Violations**:
- Review FraudAgent output in logs
- Ensure no forbidden terms appear in user responses

### Performance Optimization
- Adjust `max_cached_workflows` in worker configuration
- Optimize web search timeouts based on needs
- Consider parallel agent execution for better throughput

## Security Considerations

This sample demonstrates critical security patterns:

1. **Information Boundaries**: Clear separation between public and private agent access
2. **Output Sanitization**: Multiple validation layers prevent information leakage
3. **Fraud Method Protection**: Detection algorithms never exposed to users
4. **Prompt Injection Defense**: Input validation and manipulation detection

**Important**: In production, additional security measures would include:
- Encryption of sensitive workflow data
- Role-based access controls for human reviewers
- Audit logging of all decisions and reasoning
- Regular security assessments of agent outputs

---

This sample showcases the power of combining Temporal's durable execution with OpenAI Agents SDK for business-critical workflows requiring AI decision-making, robust guardrails, and seamless human integration. 