# Expense System UI Specification

## Overview
The Expense System UI is a FastAPI-based web application that provides both a web interface and REST API for managing expense requests. It integrates with Temporal workflows through signal mechanisms.

## System Components

### Data Model
- **ExpenseState Enum**: Defines expense lifecycle states
  - `CREATED`: Initial state when expense is first created
  - `APPROVED`: Expense has been approved for payment
  - `REJECTED`: Expense has been denied
  - `COMPLETED`: Payment has been processed

### Storage
- **all_expenses**: In-memory dictionary mapping expense IDs to their current state
- **workflow_map**: Maps expense IDs to Temporal workflow IDs for signal sending

## API Endpoints

### Parameter Validation
All endpoints use FastAPI's automatic parameter validation:
- Missing required parameters return HTTP 422 (Unprocessable Entity)
- Invalid parameter types return HTTP 422 (Unprocessable Entity)
- This validation occurs before endpoint-specific business logic

### 1. Home/List View (`GET /` or `GET /list`)
**Purpose**: Display all expenses in an HTML table format

**Response**: HTML page containing:
- Page title "SAMPLE EXPENSE SYSTEM"
- Navigation link to HOME
- Table with columns: Expense ID, Status, Action
- Action buttons for CREATED expenses (APPROVE/REJECT)
- Sorted expense display by ID

**Business Rules**:
- Only CREATED expenses show action buttons
- Expenses are displayed in sorted order by ID

### 2. Action Handler (`GET /action`)
**Purpose**: Process expense state changes (approve/reject/payment)

**Parameters**:
- `type` (required): Action type - "approve", "reject", or "payment"
- `id` (required): Expense ID
- `is_api_call` (optional): "true" for API calls, "false" for UI calls

**Business Rules**:
- `approve`: Changes CREATED → APPROVED
- `reject`: Changes CREATED → REJECTED  
- `payment`: Changes APPROVED → COMPLETED
- Invalid IDs return HTTP 200 with error message in response body
- Invalid action types return HTTP 200 with error message in response body
- State changes from CREATED to APPROVED/REJECTED trigger workflow notifications
- API calls return "SUCCEED" on success
- UI calls redirect to list view after success

**Error Handling**:
- API calls return HTTP 200 with "ERROR:INVALID_ID" or "ERROR:INVALID_TYPE" in response body
- UI calls return HTTP 200 with descriptive messages like "Invalid ID" or "Invalid action type" in response body

### 3. Create Expense (`GET /create`)
**Purpose**: Create a new expense entry

**Parameters**:
- `id` (required): Unique expense ID
- `is_api_call` (optional): "true" for API calls, "false" for UI calls

**Business Rules**:
- Expense ID must be unique
- New expenses start in CREATED state
- Duplicate IDs return HTTP 200 with error message in response body

**Error Handling**:
- API calls return HTTP 200 with "ERROR:ID_ALREADY_EXISTS" in response body
- UI calls return HTTP 200 with descriptive message "ID already exists" in response body

### 4. Status Check (`GET /status`)
**Purpose**: Retrieve current expense state

**Parameters**:
- `id` (required): Expense ID

**Response**: Current expense state as string
**Error Handling**: Returns HTTP 200 with "ERROR:INVALID_ID" in response body for unknown IDs

### 5. Workflow Registration (`POST /registerWorkflow`)
**Purpose**: Register Temporal workflow ID for expense state change signals

**Parameters**:
- `id` (query): Expense ID
- `workflow_id` (form): Temporal workflow ID

**Business Rules**:
- Expense must exist and be in CREATED state
- Workflow ID is stored for later signal sending
- Enables workflow signal notification on state changes

**Error Handling**:
- HTTP 200 with "ERROR:INVALID_ID" in response body for unknown expenses
- HTTP 200 with "ERROR:INVALID_STATE" in response body for non-CREATED expenses

## Workflow Integration

### Signal Mechanism
- When expenses transition from CREATED to APPROVED/REJECTED, registered workflows are signaled
- Uses Temporal's workflow signal mechanism
- Workflow IDs are stored and used to send signals to workflows

### Error Handling
- Failed signal sending is logged but doesn't affect UI operations
- Invalid or non-existent workflow IDs are handled gracefully

## User Interface

### Web Interface Features
- Clean HTML table display
- Color-coded action buttons (green for APPROVE, red for REJECT)
- Real-time state display
- Navigation between views

### API Interface Features
- RESTful endpoints for programmatic access
- Consistent error response format
- Support for both sync and async operations

## Non-Functional Requirements

### Concurrency
- Thread-safe in-memory storage operations
- Handles concurrent API and UI requests

### Error Recovery
- Graceful handling of workflow signal failures
- Input validation on all endpoints (422 for missing/invalid parameters, 200 with error messages for business logic errors)
- Descriptive error messages in response body

### Logging
- State change operations are logged
- Workflow registration and signal sending logged
- Error conditions logged for debugging

## Security Considerations
- Input validation on all parameters
- Protection against duplicate ID creation
- Secure handling of Temporal workflow IDs

## Scalability Notes
- Current implementation uses in-memory storage
- Designed for demonstration/development use
- Production deployment would require persistent storage 