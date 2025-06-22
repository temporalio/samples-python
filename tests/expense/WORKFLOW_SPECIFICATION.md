# Expense Workflow and Activities Specification

## Overview
The Expense Processing System demonstrates a human-in-the-loop workflow pattern using Temporal. It processes expense requests through a multi-step approval workflow with asynchronous activity completion.

## Business Process Flow

### Workflow Steps
1. **Create Expense Report**: Initialize a new expense in the external system
2. **Wait for Human Decision**: Wait for approval/rejection via external UI (asynchronous completion)
3. **Process Payment** (conditional): Execute payment if approved

### Decision Logic
- **APPROVED**: Continue to payment processing → Return "COMPLETED"
- **Any other value**: Skip payment processing → Return empty string ""
  - This includes: "REJECTED", "DENIED", "PENDING", "CANCELLED", or any unknown value
- **ERROR**: Propagate failure to workflow caller

## Architecture Components

### Core Entities
- **Workflow**: `SampleExpenseWorkflow` - Main orchestration logic
- **Activities**: Three distinct activities for each business step
- **External System**: HTTP-based expense management UI
- **Task Tokens**: Enable asynchronous activity completion from external systems

### External Integration
- **Expense UI Server**: HTTP API at `localhost:8099`
- **Async Completion**: UI system completes activities via Temporal client
- **Human Interaction**: Web-based approval/rejection interface

## Implementation Specifications

### Workflow Definition

#### `SampleExpenseWorkflow`
```python
@workflow.defn
class SampleExpenseWorkflow:
    @workflow.run
    async def run(self, expense_id: str) -> str
```

**Input Parameters**:
- `expense_id`: Unique identifier for the expense request

**Return Values**:
- Success (Approved): `"COMPLETED"`
- Success (Rejected): `""` (empty string)
- Failure: Exception/error propagated

**Timeout Configuration**:
- Step 1 (Create): 10 seconds
- Step 2 (Wait): 10 minutes (human approval timeout)
- Step 3 (Payment): 10 seconds

### Activity Definitions

#### 1. Create Expense Activity

**Purpose**: Initialize expense record in external system

**Function Signature**: `create_expense_activity(expense_id: str) -> None`

**Business Rules**:
- Validate expense_id is not empty
- HTTP GET to `/create?is_api_call=true&id={expense_id}`
- Success condition: Response body equals "SUCCEED"
- Any other response triggers exception

**Error Handling**:
- Empty expense_id: `ValueError` with message "expense id is empty"
- Whitespace-only expense_id: `ValueError` (same as empty)
- HTTP errors: `httpx.HTTPStatusError` propagated to workflow
- Server error responses: `Exception` with specific error message (e.g., "ERROR:ID_ALREADY_EXISTS")
- Network failures: Connection timeouts and DNS resolution errors propagated

#### 2. Wait for Decision Activity

**Purpose**: Register for async completion and wait for human approval

**Function Signature**: `wait_for_decision_activity(expense_id: str) -> str`

**Async Completion Pattern**:
The activity demonstrates asynchronous activity completion. It registers itself for external completion using its task token, then calls `activity.raise_complete_async()` to signal that it will complete later without blocking the worker. This pattern enables human-in-the-loop workflows where activities can wait as long as necessary for external decisions without consuming worker resources or timing out.

**Business Logic**:
1. Validate expense_id is not empty
2. Extract activity task token from context
3. Register callback with external system via HTTP POST
4. Call `activity.raise_complete_async()` to signal async completion
5. When a human approves or rejects the expense, an external process uses the stored task token to call `workflow_client.get_async_activity_handle(task_token).complete()`, providing the decision result

**HTTP Integration**:
- **Endpoint**: POST `/registerCallback?id={expense_id}`
- **Payload**: `task_token` as form data (hex-encoded)
- **Success Response**: "SUCCEED"

**Completion Values**:
- `"APPROVED"`: Expense approved for payment
- `"REJECTED"`: Expense denied
- `"DENIED"`, `"PENDING"`, `"CANCELLED"`: Also treated as rejection
- Any other value: Treated as rejection (workflow returns empty string)

**Error Scenarios**:
- Empty expense_id: Immediate validation error
- HTTP registration failure: Activity fails immediately
- Registration success but completion timeout: Temporal timeout handling

#### 3. Payment Activity

**Purpose**: Process payment for approved expenses

**Function Signature**: `payment_activity(expense_id: str) -> None`

**Business Rules**:
- Only called for approved expenses
- Validate expense_id is not empty
- HTTP GET to `/action?is_api_call=true&type=payment&id={expense_id}`
- Success condition: Response body equals "SUCCEED"

**Error Handling**:
- Empty expense_id: `ValueError` with message "expense id is empty"
- HTTP errors: `httpx.HTTPStatusError` propagated to workflow
- Payment failure: `Exception` with specific error message (e.g., "ERROR:INSUFFICIENT_FUNDS")
- Network failures: Connection timeouts and DNS resolution errors propagated

## State Management

### Activity Completion Flow
1. **Synchronous Activities**: Create and Payment activities complete immediately
2. **Asynchronous Activity**: Wait for Decision completes externally

### Task Token Lifecycle
1. Activity extracts task token from execution context
2. Token registered with external system via HTTP POST
3. External system stores token mapping to expense ID
4. Human makes decision via web UI
5. UI system calls Temporal client to complete activity
6. Activity returns decision value to workflow

### External System Integration
- **Storage**: In-memory expense state management
- **Callbacks**: Task token to expense ID mapping
- **Completion**: Temporal client async activity completion
- **Error Recovery**: Graceful handling of completion failures

## Error Handling Patterns

### Validation Errors
- **Trigger**: Empty or invalid input parameters
- **Behavior**: Immediate activity/workflow failure
- **Retry**: Not applicable (validation errors are non-retryable)

### HTTP Communication Errors
- **Network Failures**: Connection timeouts, DNS resolution
- **Server Errors**: 5xx responses from expense system
- **Retry Behavior**: Follows Temporal's default retry policy
- **Final Failure**: Propagated to workflow after retries exhausted

### External System Errors
- **Business Logic Errors**: Duplicate expense IDs, invalid states
- **Response Format**: Error messages in HTTP response body (e.g., "ERROR:ID_ALREADY_EXISTS")
- **Handling**: Converted to application errors with descriptive messages
- **Tested Examples**: "ERROR:INVALID_ID", "ERROR:INSUFFICIENT_FUNDS", "ERROR:INVALID_STATE"

### Async Completion Errors
- **Registration Failure**: Activity fails immediately if callback registration fails
- **Completion Timeout**: Temporal enforces activity timeout (10 minutes)
- **Invalid Completion**: External system error handling for malformed completions

## Timeout Configuration

### Activity Timeouts
- **Create Expense**: 10 seconds (fast operation)
- **Wait for Decision**: 10 minutes (human approval window)
- **Payment Processing**: 10 seconds (automated operation)

### Timeout Behavior
- **Exceeded**: Activity marked as failed by Temporal
- **Retry**: Follows activity retry policy
- **Workflow Impact**: Timeout failures propagate to workflow



## Testing Patterns

### Mock Testing Approach
The system supports comprehensive testing with mocked activities:

#### Test Patterns
```python
@activity.defn(name="create_expense_activity")
async def create_expense_mock(expense_id: str) -> None:
    return None  # Success mock

@activity.defn(name="wait_for_decision_activity") 
async def wait_for_decision_mock(expense_id: str) -> str:
    return "APPROVED"  # Decision mock

# Testing async completion behavior:
from temporalio.activity import _CompleteAsyncError
with pytest.raises(_CompleteAsyncError):
    await activity_env.run(wait_for_decision_activity, "test-expense")
```

### Test Scenarios
1. **Happy Path**: All activities succeed, expense approved
2. **Rejection Path**: Expense rejected, payment skipped
3. **Failure Scenarios**: Activity failures at each step
4. **Mock Server Testing**: HTTP interactions with test server
5. **Async Completion Testing**: Simulated callback completion (expects `_CompleteAsyncError`)
6. **Decision Value Testing**: All possible decision values (APPROVED, REJECTED, DENIED, PENDING, CANCELLED, UNKNOWN)
7. **Retryable Failures**: Activities that fail temporarily and then succeed on retry
8. **Parameter Validation**: Empty and whitespace-only expense IDs
9. **Logging Behavior**: Verify activity logging works correctly
10. **Server Error Responses**: Specific error formats like "ERROR:ID_ALREADY_EXISTS"

### Mock Server Integration
- **HTTP Mocking**: Uses test frameworks to mock HTTP server responses
- **Delayed Completion**: Simulates human approval delays in tests

### Edge Case Testing
Tests include comprehensive coverage of edge cases and error scenarios:

#### Retry Behavior Testing
- **Transient Failures**: Activities that fail on first attempts but succeed after retries
- **Retry Counting**: Verification that activities retry the expected number of times
- **Mixed Scenarios**: Different activities failing and recovering independently

#### Parameter Validation Testing
- **Empty Strings**: Expense IDs that are completely empty (`""`)
- **Whitespace-Only**: Expense IDs containing only spaces (`"   "`)
- **Non-Retryable Errors**: Validation failures that should not be retried

#### Logging Verification
- **Activity Logging**: Ensures activity.logger.info() calls work correctly
- **Workflow Logging**: Verification of workflow-level logging behavior
- **Log Content**: Checking that log messages contain expected information

#### Server Error Response Testing
- **Specific Error Codes**: Testing responses like "ERROR:ID_ALREADY_EXISTS"
- **HTTP Status Errors**: Network-level HTTP errors vs application errors
- **Error Message Propagation**: Ensuring error details reach the workflow caller

