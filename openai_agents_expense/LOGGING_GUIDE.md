# Temporal Logging Guide for OpenAI Agents Expense Processing

This document describes the comprehensive logging system added to the OpenAI Agents Expense Processing workflow and related activities. The logging provides excellent visibility into the application flow through Temporal traces.

## Overview

The logging system uses structured logging with emojis and consistent `extra` fields to make Temporal traces easy to read and understand. Each log entry includes:

- **Descriptive emoji prefixes** for visual identification
- **Structured extra fields** for filtering and searching
- **Stage tracking** to show progression through the workflow
- **Error categorization** for debugging
- **Performance timing** for optimization

## Workflow Logging (`expense_workflow.py`)

### Main Workflow Stages

#### 🚀 Workflow Initialization
```python
logger.info(f"🚀 WORKFLOW_START: Processing expense {expense_report.expense_id}")
```
- Logs expense details (ID, amount, vendor, description, department)
- Includes metadata like international travel and receipt status

#### 📋 Agent Execution Tracking
Each AI agent execution is tracked with:
- **Agent Start**: `📋 AGENT_START: CategoryAgent processing expense`
- **Agent Complete**: `✅ AGENT_COMPLETE: CategoryAgent finished`
- **Duration tracking**: Agent execution time in seconds
- **Confidence monitoring**: Logs confidence scores and thresholds

#### ⚡ Parallel Processing Visibility
```python
logger.info(f"⚡ PARALLEL_START: Policy evaluation and fraud assessment")
logger.info(f"✅ PARALLEL_COMPLETE: Policy and fraud assessment finished")
```
- Tracks parallel execution of PolicyEvaluationAgent and FraudAgent
- Logs combined results and duration

#### 🔀 Decision Branch Tracking
```python
logger.info(f"🔀 DECISION_BRANCH: Processing decision '{final_decision.decision}'")
```
- Tracks which decision path is taken
- Includes decision confidence and reasoning type

#### 👥 Human-in-the-Loop Integration
- **Human Escalation**: `👥 HUMAN_ESCALATION: Escalating to human review`
- **Human Decision Wait**: `⏳ HUMAN_WAIT: Waiting for human decision`
- **Human Decision Received**: `👤 HUMAN_DECISION: Human decision received`

#### 💳 Payment Processing
- **Payment Start**: `💳 PAYMENT_START: Processing payment`
- **Payment Complete**: `✅ PAYMENT_SUCCESS: Payment processed successfully`

### Error Handling and Recovery

#### 🚨 Error Scenarios
- **Workflow Errors**: `🚨 WORKFLOW_ERROR: Expense processing failed`
- **Escalation Failures**: `🚨 ESCALATION_FAILURE: Failed to escalate`
- **Recovery Tracking**: Logs error recovery attempts and outcomes

#### ⚠️ Confidence Monitoring
- **Low Confidence Warnings**: `⚠️ LOW_CONFIDENCE: CategoryAgent low confidence`
- **Threshold Tracking**: Logs which agents triggered escalation
- **Confidence Summaries**: Aggregated confidence issue reporting

### Status Updates
```python
logger.info(f"📊 STATUS_UPDATE: Status changed for {expense_id}")
```
- Tracks status transitions with timestamps
- Includes previous and new status for audit trail

## Activity Logging

### Web Search Activity (`web_search.py`)

#### 🔍 Search Operations
- **Search Start**: `🔍 WEB_SEARCH_START: Starting web search`
- **Query Sanitization**: `🧹 QUERY_SANITIZED: Search query was sanitized`
- **Search Execution**: `🌐 SEARCH_EXECUTING: Performing web search`
- **Results Analysis**: `🔬 ANALYSIS_START: Analyzing search results`

#### 📊 Result Processing
- **Mock Generation**: Different vendor types logged (🏪 major retailer, ✈️ airline, 🏢 professional)
- **Legitimacy Assessment**: `✅ OFFICIAL_WEBSITE: Found official website`
- **Confidence Calculation**: `📊 CONFIDENCE_CALC: Calculated confidence score`

### Expense Activities (`expense/activities.py`)

#### 📝 Create Expense Activity
- **Activity Start**: `📝 CREATE_EXPENSE_START: Creating expense entry`
- **HTTP Requests**: `🌐 HTTP_REQUEST: Making HTTP request to expense server`
- **Response Processing**: `📨 HTTP_RESPONSE: Received response from expense server`

#### ⏳ Wait for Decision Activity
- **Async Setup**: `⏳ WAIT_DECISION_START: Starting async wait for human decision`
- **Task Token**: `🔑 TASK_TOKEN: Generated task token for async completion`
- **Callback Registration**: `📞 CALLBACK_REGISTRATION: Registering callback`

#### 💳 Payment Activity
- **Payment Processing**: `💳 PAYMENT_START: Starting payment processing`
- **Success/Failure**: Clear logging of payment outcomes

## AI Agent Logging

### Category Agent (`category_agent.py`)

#### 📋 Agent Execution Flow
- **Agent Start**: `📋 CATEGORY_AGENT_START: Starting expense categorization`
- **Agent Creation**: `🤖 AGENT_CREATION: Creating CategoryAgent instance`
- **Input Preparation**: `🎯 AGENT_INPUT: Prepared agent input`
- **Execution**: `🚀 AGENT_EXECUTION: Running CategoryAgent`
- **Response Parsing**: `🔍 RESPONSE_PARSING: Parsing agent response`

#### 🔧 Fallback Handling
- **Fallback Start**: `🔧 FALLBACK_START: Starting fallback categorization`
- **Keyword Analysis**: `🔍 KEYWORD_ANALYSIS: Analyzing keywords for categorization`
- **Category Determination**: `🎯 CATEGORY_DETERMINED: Fallback category determined`

### Response Agent (`response_agent.py`)

#### 📝 Response Generation
- **Agent Start**: `📝 RESPONSE_AGENT_START: Starting response generation`
- **Input Preparation**: `🎯 AGENT_INPUT: Prepared response agent input`
- **Content Validation**: `✅ RESPONSE_VALIDATED: Response content validated`
- **Content Sanitization**: `⚠️ CONTENT_SANITIZED: Removed sensitive term`

#### 🔧 Fallback Messages
- **Template Generation**: Different message types (📝 approval, ❌ rejection, 👥 review)
- **Decision-specific logging**: Tracks message generation for each decision type

## Log Structure and Fields

### Standard Extra Fields
```python
extra={
    "expense_id": expense_report.expense_id,
    "agent": "CategoryAgent",
    "workflow_stage": "categorization",
    "step": 1,
    "stage": "start"
}
```

### Performance Fields
- `duration_seconds`: Agent execution time
- `confidence`: Agent confidence scores
- `response_length`: Response/input text lengths

### Error Fields
- `error`: Error message
- `error_type`: Exception class name
- `escalation_trigger`: Reason for escalation

### Decision Tracking Fields
- `decision`: Final decision type
- `decision_path`: Which path was taken
- `is_mandatory_escalation`: Whether escalation was mandatory

## Using the Logs

### Temporal Web UI
The structured logging provides rich information in the Temporal Web UI:

1. **Workflow Overview**: See the complete flow from initialization to completion
2. **Agent Performance**: Track individual agent execution times and confidence
3. **Decision Path**: Understand which path the expense took through the system
4. **Error Analysis**: Quickly identify and debug issues
5. **Human Interaction**: Track when and why human review was required

### Log Filtering
Use the `extra` fields to filter logs:
- By agent: `agent=CategoryAgent`
- By stage: `workflow_stage=categorization`
- By expense: `expense_id=EXP-12345`
- By errors: `error_type=json.JSONDecodeError`

### Performance Monitoring
Track timing information:
- Agent execution duration
- Parallel processing efficiency
- Human decision wait times
- Payment processing speed

## Best Practices

1. **Consistent Structure**: All logs follow the same pattern with emojis and extra fields
2. **Error Context**: Errors include full context for debugging
3. **Performance Tracking**: Duration logged for all major operations
4. **Security**: Sensitive information is sanitized in public-facing logs
5. **Audit Trail**: Status changes and decision points are fully logged

This logging system provides comprehensive visibility into the OpenAI Agents Expense Processing workflow, making it easy to understand the application flow, debug issues, and monitor performance through Temporal traces. 