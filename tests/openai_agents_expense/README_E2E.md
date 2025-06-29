# End-to-End Tests for OpenAI Agents Expense Processing

This directory contains comprehensive end-to-end tests that validate the complete workflow from starter.py execution through workflow completion, simulating real-world usage scenarios.

## 🎯 Test Coverage

The E2E test suite covers all starter.py scenarios with the `-w` (wait) flag:

### Test Cases

1. **`test_expense_1_auto_approval`**
   - Tests office supplies expense (Staples, $45.00)
   - Should auto-approve without human intervention
   - Validates complete workflow: AI processing → approval → payment

2. **`test_expense_2_human_approval`** 
   - Tests international travel expense (British Airways, $400.00)
   - Should escalate to human review then approve
   - Validates escalation path: AI processing → human review → approval → payment

3. **`test_expense_3_human_rejection`**
   - Tests suspicious vendor expense (Joe's Totally Legit Restaurant, $200.00)
   - Should escalate to human review then reject
   - Validates rejection path: AI processing → human review → rejection

4. **`test_all_expenses_batch_processing`**
   - Tests processing all three expenses simultaneously
   - Equivalent to `python starter.py -e all -w`
   - Validates concurrent workflow execution

5. **`test_ui_integration_mock_server`**
   - Tests the expense UI server endpoints
   - Validates FastAPI integration and human decision interface

6. **`test_environment_setup`**
   - Validates environment configuration
   - Checks .env file and OpenAI API key availability

## 🚀 Quick Start

### Prerequisites

1. **Environment Setup**
   ```bash
   # Create .env file in samples-python-2/
   echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
   ```

2. **Temporal Server**
   ```bash
   # Start Temporal development server
   temporal server start-dev
   ```

3. **Install Dependencies**
   ```bash
   # Install E2E test dependencies
   pip install -r tests/openai_agents_expense/requirements-e2e.txt
   ```

### Running Tests

#### Option 1: Using the Test Runner (Recommended)
```bash
# Run all E2E tests
python tests/openai_agents_expense/run_e2e_tests.py

# Run with verbose output
python tests/openai_agents_expense/run_e2e_tests.py --verbose

# Run single test case
python tests/openai_agents_expense/run_e2e_tests.py --single expense_1

# Just check environment setup
python tests/openai_agents_expense/run_e2e_tests.py --env-only
```

#### Option 2: Using pytest directly
```bash
# Run all E2E tests
pytest tests/openai_agents_expense/test_starter_e2e.py -v

# Run specific test
pytest tests/openai_agents_expense/test_starter_e2e.py::TestStarterE2E::test_expense_1_auto_approval -v

# Run with coverage
pytest tests/openai_agents_expense/test_starter_e2e.py --cov=openai_agents_expense
```

## 🔧 Test Architecture

### Mocking Strategy

The tests use comprehensive mocking to ensure reliable, fast execution:

- **HTTP Client Mocking**: All external HTTP calls (expense server) are mocked
- **Human Decision Simulation**: Human approval/rejection decisions are automated
- **OpenAI API**: Uses real OpenAI API calls (requires valid API key)
- **Temporal Server**: Uses real Temporal server for workflow execution

### Test Fixtures

- **`setup_env`**: Automatically loads .env file and validates OpenAI API key
- **`mock_expense_server`**: Simulates the expense server HTTP endpoints
- **`mock_human_decision`**: Provides deterministic human decision outcomes

### Key Features

- **Parallel Execution**: Tests can run concurrently with unique task queues
- **State Isolation**: Each test clears state to avoid interference
- **Real Workflow Execution**: Uses actual Temporal workflows and activities
- **Comprehensive Assertions**: Validates both workflow results and intermediate states

## 📊 Expected Results

| Test Case | Expense ID | Expected Result | Decision Path |
|-----------|------------|-----------------|---------------|
| Expense 1 | EXP-2024-001 | COMPLETED | Auto-approval |
| Expense 2 | EXP-2024-002 | COMPLETED | Human approval |
| Expense 3 | EXP-2024-003 | REJECTED | Human rejection |

## 🐛 Troubleshooting

### Common Issues

1. **Missing OpenAI API Key**
   ```
   Error: OPENAI_API_KEY not found in .env file
   Solution: Create .env file with your OpenAI API key
   ```

2. **Temporal Server Not Running**
   ```
   Error: Cannot connect to Temporal server
   Solution: Start with `temporal server start-dev`
   ```

3. **Port Conflicts**
   ```
   Error: Address already in use (7233)
   Solution: Stop existing Temporal server or use different port
   ```

4. **Import Errors**
   ```
   Error: ModuleNotFoundError
   Solution: Install requirements with `pip install -r requirements-e2e.txt`
   ```

### Debug Mode

For detailed debugging, run tests with maximum verbosity:
```bash
python tests/openai_agents_expense/run_e2e_tests.py --verbose
# or
pytest tests/openai_agents_expense/test_starter_e2e.py -vv -s --tb=long
```

## 🔄 CI/CD Integration

The tests are designed for CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run E2E Tests
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  run: |
    temporal server start-dev &
    sleep 5
    python tests/openai_agents_expense/run_e2e_tests.py
```

## 📝 Adding New Tests

To add new test cases:

1. **Create Test Method**
   ```python
   @pytest.mark.asyncio
   async def test_your_scenario(self, mock_expense_server):
       # Test implementation
   ```

2. **Use Existing Fixtures**
   - `mock_expense_server` for HTTP mocking
   - `mock_human_decision` for human decisions
   - `setup_env` for environment validation

3. **Follow Naming Convention**
   - Use descriptive test names: `test_scenario_expected_outcome`
   - Add docstrings explaining the test purpose

## 🎯 Best Practices

- **Use Real API Keys**: Tests use actual OpenAI API for realistic validation
- **Mock External Dependencies**: All HTTP calls are mocked for reliability
- **Isolated State**: Each test runs independently with clean state
- **Comprehensive Assertions**: Validate both workflow results and intermediate states
- **Clear Documentation**: Each test documents its expected behavior

---

*These E2E tests ensure that the OpenAI Agents Expense Processing system works correctly in realistic scenarios, providing confidence in the complete workflow from start to finish.* 