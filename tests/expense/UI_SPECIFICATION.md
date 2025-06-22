# Expense System UI Specification

## Overview
The Expense System UI is a FastAPI-based web application that provides both a web interface and REST API for managing expense requests. It integrates with Temporal workflows through callback mechanisms.

## System Components

### Data Model
- **ExpenseState Enum**: Defines expense lifecycle states
  - `CREATED`: Initial state when expense is first created
  - `APPROVED`: Expense has been approved for payment
  - `REJECTED`: Expense has been denied
  - `COMPLETED`: Payment has been processed

### Storage
- **all_expenses**: In-memory dictionary mapping expense IDs to their current state
- **token_map**: Maps expense IDs to Temporal activity task tokens for workflow callbacks

## API Endpoints

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
- Invalid IDs return 400 error
- Invalid action types return 400 error
- State changes from CREATED to APPROVED/REJECTED trigger workflow notifications
- API calls return "SUCCEED" on success
- UI calls redirect to list view after success

**Error Handling**:
- API calls return "ERROR:INVALID_ID" or "ERROR:INVALID_TYPE"
- UI calls return HTTP 400 with descriptive messages

### 3. Create Expense (`GET /create`)
**Purpose**: Create a new expense entry

**Parameters**:
- `id` (required): Unique expense ID
- `is_api_call` (optional): "true" for API calls, "false" for UI calls

**Business Rules**:
- Expense ID must be unique
- New expenses start in CREATED state
- Duplicate IDs return 400 error

**Error Handling**:
- API calls return "ERROR:ID_ALREADY_EXISTS"
- UI calls return HTTP 400 with descriptive message

### 4. Status Check (`GET /status`)
**Purpose**: Retrieve current expense state

**Parameters**:
- `id` (required): Expense ID

**Response**: Current expense state as string
**Error Handling**: Returns "ERROR:INVALID_ID" for unknown IDs

### 5. Callback Registration (`POST /registerCallback`)
**Purpose**: Register Temporal workflow callback for expense state changes

**Parameters**:
- `id` (query): Expense ID
- `task_token` (form): Hex-encoded Temporal task token

**Business Rules**:
- Expense must exist and be in CREATED state
- Task token must be valid hex format
- Enables workflow notification on state changes

**Error Handling**:
- "ERROR:INVALID_ID" for unknown expenses
- "ERROR:INVALID_STATE" for non-CREATED expenses
- "ERROR:INVALID_FORM_DATA" for invalid tokens

## Workflow Integration

### Callback Mechanism
- When expenses transition from CREATED to APPROVED/REJECTED, registered callbacks are triggered
- Uses Temporal's async activity completion mechanism
- Task tokens are stored and used to complete workflow activities

### Error Handling
- Failed callback completions are logged but don't affect UI operations
- Invalid or expired tokens are handled gracefully

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
- Graceful handling of workflow callback failures
- Input validation on all endpoints
- Descriptive error messages

### Logging
- State change operations are logged
- Callback registration and completion logged
- Error conditions logged for debugging

## Security Considerations
- Input validation on all parameters
- Protection against duplicate ID creation
- Secure handling of Temporal task tokens

## Scalability Notes
- Current implementation uses in-memory storage
- Designed for demonstration/development use
- Production deployment would require persistent storage 