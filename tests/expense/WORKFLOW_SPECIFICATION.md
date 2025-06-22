# Expense Workflow and Activities Specification

## Overview
The Expense Processing System demonstrates a human-in-the-loop workflow pattern using Temporal. It processes expense requests through a multi-step approval workflow with asynchronous activity completion. The system is implemented in both Python and Go with identical business logic and behavior.

## Business Process Flow

### Workflow Steps
1. **Create Expense Report**: Initialize a new expense in the external system
2. **Wait for Human Decision**: Wait for approval/rejection via external UI (asynchronous completion)
3. **Process Payment** (conditional): Execute payment if approved

### Decision Logic
- **APPROVED**: Continue to payment processing → Return "COMPLETED"
- **REJECTED**: Skip payment processing → Return empty string ""
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

#### Python Implementation (`SampleExpenseWorkflow`)
```python
@workflow.defn
class SampleExpenseWorkflow:
    @workflow.run
    async def run(self, expense_id: str) -> str
```

#### Go Implementation (`SampleExpenseWorkflow`)
```go
func SampleExpenseWorkflow(ctx workflow.Context, expenseID string) (result string, err error)
```

**Input Parameters**:
- `expense_id`/`expenseID`: Unique identifier for the expense request

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

**Python**: `create_expense_activity(expense_id: str) -> None`
**Go**: `CreateExpenseActivity(ctx context.Context, expenseID string) error`

**Business Rules**:
- Validate expense_id is not empty
- HTTP GET to `/create?is_api_call=true&id={expense_id}`
- Success condition: Response body equals "SUCCEED"
- Any other response triggers exception

**Error Handling**:
- Empty expense_id: `ValueError`/`errors.New`
- HTTP errors: Propagated to workflow
- Unexpected response: Exception with response body

#### 2. Wait for Decision Activity

**Purpose**: Register for async completion and wait for human approval

**Python**: `wait_for_decision_activity(expense_id: str) -> str`
**Go**: `WaitForDecisionActivity(ctx context.Context, expenseID string) (string, error)`

**Async Completion Pattern**:
- **Python**: Raises `activity.raise_complete_async()` 
- **Go**: Returns `activity.ErrResultPending`

**Business Logic**:
1. Validate expense_id is not empty
2. Extract activity task token from context
3. Register callback with external system via HTTP POST
4. Signal async completion to Temporal
5. External system later completes activity with decision

**HTTP Integration**:
- **Endpoint**: POST `/registerCallback?id={expense_id}`
- **Payload**: `task_token` as form data (hex-encoded)
- **Success Response**: "SUCCEED"

**Completion Values**:
- `"APPROVED"`: Expense approved for payment
- `"REJECTED"`: Expense denied
- Other values: Treated as rejection

**Error Scenarios**:
- Empty expense_id: Immediate validation error
- HTTP registration failure: Activity fails immediately
- Registration success but completion timeout: Temporal timeout handling

#### 3. Payment Activity

**Purpose**: Process payment for approved expenses

**Python**: `payment_activity(expense_id: str) -> None`
**Go**: `PaymentActivity(ctx context.Context, expenseID string) error`

**Business Rules**:
- Only called for approved expenses
- Validate expense_id is not empty
- HTTP GET to `/action?is_api_call=true&type=payment&id={expense_id}`
- Success condition: Response body equals "SUCCEED"

**Error Handling**:
- Empty expense_id: `ValueError`/`errors.New`
- HTTP errors: Propagated to workflow
- Payment failure: Exception with response body

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
- **Response Format**: Error messages in HTTP response body
- **Handling**: Converted to application errors with descriptive messages

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

### Production Considerations
- **Human Approval**: Consider longer timeouts for real-world approval processes
- **Business Hours**: May need different timeouts based on operational hours
- **Escalation**: Implement escalation workflows for timeout scenarios

## Testing Patterns

### Mock Testing Approach
Both implementations support comprehensive testing with mocked activities:

#### Python Test Patterns
```python
@activity.defn(name="create_expense_activity")
async def create_expense_mock(expense_id: str) -> None:
    return None  # Success mock

@activity.defn(name="wait_for_decision_activity") 
async def wait_for_decision_mock(expense_id: str) -> str:
    return "APPROVED"  # Decision mock
```

#### Go Test Patterns
```go
env.OnActivity(CreateExpenseActivity, mock.Anything).Return(nil).Once()
env.OnActivity(WaitForDecisionActivity, mock.Anything).Return("APPROVED", nil).Once()
```

### Test Scenarios
1. **Happy Path**: All activities succeed, expense approved
2. **Rejection Path**: Expense rejected, payment skipped
3. **Failure Scenarios**: Activity failures at each step
4. **Mock Server Testing**: HTTP interactions with test server
5. **Async Completion Testing**: Simulated callback completion

### Mock Server Integration
- **Go Implementation**: Uses `httptest.NewServer` for HTTP mocking
- **Python Implementation**: Can use similar patterns with test frameworks
- **Delayed Completion**: Simulates human approval delays in tests

## Cross-Language Compatibility

### Functional Equivalence
Both Python and Go implementations provide identical:
- **Business Logic**: Same workflow steps and decision points
- **External Integration**: Same HTTP endpoints and payloads
- **Timeout Configuration**: Same duration settings
- **Error Handling**: Equivalent error scenarios and responses

### Implementation Differences
- **Async Patterns**: Language-specific async completion mechanisms
- **Error Types**: Language-native exception/error handling
- **HTTP Libraries**: `httpx` (Python) vs `net/http` (Go)
- **Logging**: Framework-specific logging approaches

### Interoperability
- **Task Tokens**: Binary compatible between implementations
- **HTTP Payloads**: Same format for external system integration
- **Workflow Results**: Same return value semantics
- **External System**: Single UI can serve both implementations

## Production Deployment Considerations

### Scalability
- **Stateless Activities**: No local state, horizontally scalable
- **External System**: UI system should support concurrent requests
- **Task Token Storage**: Consider persistent storage for production UI

### Reliability
- **Retry Policies**: Configure appropriate retry behavior for each activity
- **Circuit Breakers**: Consider circuit breaker patterns for external HTTP calls
- **Monitoring**: Implement metrics and alerting for workflow execution

### Security
- **Task Token Security**: Protect task tokens from unauthorized access
- **HTTP Security**: Use HTTPS for production external system integration
- **Input Validation**: Comprehensive validation of expense IDs and external inputs

### Observability
- **Workflow Tracing**: Temporal provides built-in workflow execution history
- **Activity Metrics**: Monitor activity success rates and durations
- **External System Integration**: Log HTTP interactions for debugging
- **Human Approval Metrics**: Track approval rates and response times 