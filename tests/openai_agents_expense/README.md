# Testing Documentation

This directory contains comprehensive automated tests for the OpenAI Agents Expense Processing Sample.

## Test Structure

### Test Types

- **Unit Tests**: Test individual agents and components in isolation with mocked dependencies
- **Integration Tests**: Test the complete expense workflow end-to-end with mocked OpenAI responses
- **Mock Tests**: All OpenAI interactions are mocked to ensure consistent, deterministic test results

### Test Files

- `test_expense_workflow.py`: Complete test suite including unit and integration tests
- `conftest.py`: Pytest configuration and shared fixtures
- `pytest.ini`: Pytest settings and markers
- `requirements-test.txt`: Testing dependencies

## Running Tests

### Prerequisites

1. **Python Version**: Python 3.9+ required, Python 3.11+ recommended for full OpenAI testing
2. **Dependencies**: Install test requirements
   ```bash
   pip install -r tests/requirements-test.txt
   ```

### Quick Start

Use the provided test runner script:

```bash
# Run all tests
python run_tests.py

# Run only unit tests (faster)
python run_tests.py --type unit

# Run with verbose output
python run_tests.py --verbose

# Run with coverage reporting
python run_tests.py --coverage
```

### Manual pytest Commands

```bash
# Run all tests
pytest tests/

# Run only unit tests
pytest tests/ -m unit

# Run only integration tests
pytest tests/ -m integration

# Run with coverage
pytest tests/ --cov=openai_agents_expense --cov-report=html
```

## Test Coverage

The test suite covers:

### Unit Tests
- **CategoryAgent**: Expense categorization and vendor validation
- **PolicyEvaluationAgent**: Business rule evaluation and mandatory escalations
- **FraudAgent**: Fraud detection with security boundary protection
- **DecisionOrchestrationAgent**: Final decision making with confidence thresholds
- **ResponseAgent**: User response generation

### Integration Tests
- **Happy Path Workflow**: End-to-end auto-approval scenario
- **Low Confidence Escalation**: Workflow escalation when agent confidence is below thresholds
- **Mandatory Policy Escalation**: International travel and other mandatory rules
- **Error Handling**: Agent failure and retry logic

### Mock OpenAI Responses

All tests use realistic mock responses that match the expected agent outputs:

- JSON-structured responses for each agent
- Appropriate confidence scores
- Realistic business data
- Error scenarios for testing resilience

## Test Scenarios

The tests implement several key scenarios from the specification:

### Scenario 1: Happy Path Auto-Approval
- $45 office supplies from Staples Inc
- High confidence categorization
- Policy compliant
- Low fraud risk
- Expected: Auto-approval

### Scenario 3: Suspicious Vendor Detection
- Expense from non-existent vendor
- Web search validation fails
- Expected: Escalation due to fraud risk

### Scenario 5: International Travel Mandatory Escalation
- International flight expense
- Mandatory policy requirement overrides AI assessment
- Expected: Human review regardless of other factors

## Python Version Compatibility

- **Python 3.9-3.10**: Core testing works, OpenAI tests are automatically skipped
- **Python 3.11+**: Full test suite including OpenAI agent mocking

## Mocking Strategy

### OpenAI Model Mocking
- Uses `MockExpenseModel` class extending `OpenAIResponsesModel`
- Pre-defined responses for deterministic testing
- No actual OpenAI API calls made during testing

### Activity Mocking
- Web search activity mocked with realistic responses
- No external HTTP requests during tests
- Consistent vendor validation data

### Temporal Mocking
- Uses Temporal's test environment for workflow testing
- Time-skipping enabled for fast test execution
- No external Temporal server required

## Adding New Tests

### Unit Test Pattern
```python
@pytest.mark.asyncio
async def test_new_functionality(self):
    if sys.version_info < (3, 11):
        pytest.skip("OpenAI support has type errors on 3.9 and 3.11")
    
    # Import classes dynamically after version check
    from openai_agents_expense.agents.my_agent import MyAgent
    
    # Set up test data
    # Mock dependencies
    # Execute test
    # Assert results
```

### Integration Test Pattern
```python
@pytest.mark.asyncio 
async def test_new_workflow_scenario(client: Client, test_expense_report):
    if sys.version_info < (3, 11):
        pytest.skip("OpenAI support has type errors on 3.9 and 3.11")
    
    # Create mock responses
    responses = create_scenario_responses()
    
    # Set up workflow test
    # Execute workflow
    # Assert results
```

## Debugging Tests

### Verbose Output
```bash
python run_tests.py --verbose
```

### Individual Test
```bash
pytest tests/test_expense_workflow.py::TestCategoryAgent::test_categorize_office_supplies -v
```

### Test Coverage Report
```bash
python run_tests.py --coverage
# Opens htmlcov/index.html for detailed coverage report
```

## Continuous Integration

The test suite is designed to work in CI environments:

- No external dependencies required
- Fast execution with mocked services
- Clear pass/fail criteria
- Comprehensive error reporting

For CI systems, use:
```bash
python run_tests.py --type unit --coverage
``` 