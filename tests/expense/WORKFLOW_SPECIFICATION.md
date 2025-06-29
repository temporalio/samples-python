# Expense Workflow and Activities Specification

## Overview
The Expense Processing System demonstrates a human-in-the-loop workflow pattern using Temporal. It processes expense requests through a multi-step approval workflow with signal-based completion.

## Business Process Flow

### Workflow Steps
1. **Create Expense Report**: Initialize a new expense in the external system
2. **Register for Decision & Wait for Signal**: Register expense and wait for approval/rejection via external UI (signal-based completion)
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
- **Workflow Signals**: Enable workflow completion from external systems

### External Integration
- **Expense UI Server**: HTTP API at `localhost:8099`
- **Signal Completion**: UI system sends signals to workflows via Temporal client
- **Human Interaction**: Web-based approval/rejection interface

## Implementation Specifications

### Workflow Definition

#### `SampleExpenseWorkflow`
```python
@workflow.defn
class SampleExpenseWorkflow:
    def __init__(self) -> None:
        self.expense_decision: str = ""

    @workflow.signal
    async def expense_decision_signal(self, decision: str) -> None:
        self.expense_decision = decision

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

#### 2. Register for Decision Activity

**Purpose**: Register expense for human decision and return immediately

**Function Signature**: `register_for_decision_activity(expense_id: str) -> None`

**Signal-Based Pattern**:
The activity demonstrates a signal-based human-in-the-loop pattern. It simply registers the expense for decision and completes immediately. The workflow then waits for a signal from an external system. This pattern enables human-in-the-loop workflows where workflows can wait as long as necessary for external decisions using Temporal's signal mechanism.

**Business Logic**:
1. Validate expense_id is not empty
2. Log that the expense has been registered for decision
3. Return immediately (no HTTP calls or external registration)
4. The workflow then waits for a signal using `workflow.wait_condition()`
5. When a human approves or rejects the expense, an external process sends a signal to the workflow using `workflow_handle.signal()`

**Signal Integration**:
- **Signal Name**: `expense_decision_signal`
- **Signal Payload**: Decision string ("APPROVED", "REJECTED", etc.)
- **Workflow Registration**: External system must know the workflow ID to send signals

**Completion Values**:
- `"APPROVED"`: Expense approved for payment
- `"REJECTED"`: Expense denied
- `"DENIED"`, `"PENDING"`, `"CANCELLED"`: Also treated as rejection
- Any other value: Treated as rejection (workflow returns empty string)

**Error Scenarios**:
- Empty expense_id: Immediate validation error
- Signal timeout: Temporal timeout handling (workflow-level timeout)
- Invalid signal payload: Handled gracefully by workflow

#### 3. Payment Activity

**Purpose**: Process payment for approved expenses

**Function Signature**: `payment_activity(expense_id: str) -> None`

**Business Rules**:
- Only called for approved expenses
- Validate expense_id is not empty
- HTTP POST to `/action` with form data: `is_api_call=true`, `type=payment`, `id={expense_id}`
- Success condition: Response body equals "SUCCEED"

**Error Handling**:
- Empty expense_id: `ValueError` with message "expense id is empty"
- HTTP errors: `httpx.HTTPStatusError` propagated to workflow
- Payment failure: `Exception` with specific error message (e.g., "ERROR:INSUFFICIENT_FUNDS")
- Network failures: Connection timeouts and DNS resolution errors propagated

## State Management

### Activity Completion Flow
1. **Synchronous Activities**: Create, Register, and Payment activities complete immediately
2. **Signal-Based Waiting**: Workflow waits for external signal after registration

### Signal Lifecycle
1. Workflow starts and registers expense for decision
2. External system stores workflow ID to expense ID mapping
3. Human makes decision via web UI
4. UI system calls Temporal client to send signal to workflow
5. Workflow receives signal and continues execution

### External System Integration
- **Storage**: In-memory expense state management
- **Workflow Mapping**: Workflow ID to expense ID mapping
- **Signal Completion**: Temporal client workflow signal sending
- **Error Recovery**: Graceful handling of signal failures

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

@activity.defn(name="register_for_decision_activity") 
async def register_for_decision_mock(expense_id: str) -> None:
    return None  # Registration mock

# Testing signal-based behavior:
# Activity completes immediately, no special exceptions
result = await activity_env.run(register_for_decision_activity, "test-expense")
assert result is None
```

### Test Scenarios
1. **Happy Path**: All activities succeed, expense approved
2. **Rejection Path**: Expense rejected, payment skipped
3. **Failure Scenarios**: Activity failures at each step
4. **Mock Server Testing**: HTTP interactions with test server
5. **Signal Testing**: Simulated workflow signal sending and receiving
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

