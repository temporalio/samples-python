# OpenAI Agents Expense Processing - Setup Guide

This example is now **self-contained** and includes all the components needed to run the AI-enhanced expense processing system.

## What's Included

This example contains all the necessary components:

### Core Components
- **AI Agents**: Multi-agent orchestration for intelligent expense processing
- **Workflows**: Temporal workflows that coordinate the expense processing pipeline  
- **Activities**: Temporal activities for expense operations and external integrations
- **Web UI**: Complete web interface for human review and expense management
- **Models**: Data models for expense reports and processing results

### Copied from Basic Expense Example
To make this example self-contained, the following components were copied and adapted:
- `ui.py` - Web-based expense management interface
- `expense_activities.py` - Basic expense processing activities

## Quick Start

### 1. Install Dependencies

Make sure you have the required dependencies:

```bash
# Install the expense and openai-agents dependency groups
pip install -e ".[expense,openai-agents]"
```

### 2. Set Up Environment

Set your OpenAI API key:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

### 3. Start Temporal Server

Start your local Temporal server:

```bash
temporal server start-dev
```

### 4. Start the UI Server

In a new terminal, start the expense management UI:

```bash
# From the openai_agents_expense directory
python -m openai_agents_expense.ui

```

The UI will be available at http://localhost:8099

### 5. Start the Worker

In another terminal, start the Temporal worker:

```bash
python worker.py
```

### 6. Run Expense Workflows

In a final terminal, start processing expenses:

```bash
# Process one expense (default)
python starter.py

# Process a specific expense
python starter.py -e 2

# Process all sample expenses and wait for completion
python starter.py -e all -w

# Process expense 1 and wait to see results
python starter.py -e 1 -w
```

## Monitoring and Interaction

### Temporal Web UI
- **URL**: http://localhost:8233
- **Purpose**: Monitor workflow execution, view activity logs, debug issues

### Expense Management UI  
- **URL**: http://localhost:8099
- **Purpose**: Human review interface for expenses that require manual approval
- **Features**:
  - View all expense requests
  - Approve/reject expenses that were escalated by AI agents
  - Track expense status through the processing pipeline

## How It Works

### AI-First Processing
1. **Expense Submission**: Sample expenses are submitted via the starter script
2. **AI Agent Analysis**: Multiple AI agents analyze the expense:
   - **Category Agent**: Determines expense category and validates business purpose
   - **Fraud Agent**: Detects suspicious patterns and validates vendor legitimacy  
   - **Policy Agent**: Checks compliance with company expense policies
   - **Decision Agent**: Makes final approval/rejection decisions
3. **Human Oversight**: Complex or high-risk expenses are escalated for human review
4. **Automated Actions**: Approved expenses are automatically processed for payment

### Sample Expenses
The example includes three different expense scenarios:

1. **EXP-2024-001**: Simple office supplies ($45) - Usually auto-approved
2. **EXP-2024-002**: International travel ($400) - Typically escalated for review
3. **EXP-2024-003**: Suspicious vendor ($200) - Often escalated due to fraud concerns

### Integration Points

The system integrates several components:
- **Temporal Workflows**: Orchestrate the multi-step expense processing pipeline
- **AI Agents**: Provide intelligent analysis and decision-making
- **Web UI**: Enables human review when needed
- **External APIs**: Web search for vendor validation and business context

## Testing

The example includes comprehensive automated tests:

```bash
# From repository root, run all tests
uv run pytest tests/openai_agents_expense/ -v

# Run specific test files
uv run pytest tests/openai_agents_expense/test_models.py -v
uv run pytest tests/openai_agents_expense/test_agents_unit_simple.py -v

# Run with coverage
uv run pytest tests/openai_agents_expense/ --cov=openai_agents_expense

# Run tests matching a pattern
uv run pytest tests/openai_agents_expense/ -k "agent_imports"
```

## Troubleshooting

### Common Issues

**UI not accessible**: Make sure the UI server is running on port 8099
```bash
python -m openai_agents_expense.ui
```

**Worker errors**: Ensure your OpenAI API key is set and valid
```bash
export OPENAI_API_KEY="your-key-here"
```

**Workflow failures**: Check the Temporal Web UI at http://localhost:8233 for detailed logs

**Dependencies missing**: Install the required dependency groups
```bash
pip install -e ".[expense,openai-agents]"
```

## Self-Contained Architecture

This example is completely self-contained and does not depend on external examples:

```
openai_agents_expense/
├── ui.py                    # Web-based expense management UI
  
├── activities/
│   ├── expense_activities.py   # Basic expense processing activities
│   └── web_search.py          # Web search activity for AI agents
├── workflows/              # Temporal workflows
├── ai_agents/             # AI agent implementations  
├── models.py              # Data models
├── starter.py             # Workflow starter script
├── worker.py              # Temporal worker
└── SETUP.md               # This setup guide
```

All the necessary components from the basic `expense` example have been copied and integrated, making this a complete, runnable example that demonstrates AI-enhanced expense processing with human oversight capabilities. 