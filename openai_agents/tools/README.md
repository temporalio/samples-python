# Tools Examples

Demonstrations of various OpenAI agent tools integrated with Temporal workflows.

*Adapted from [OpenAI Agents SDK tools examples](https://github.com/openai/openai-agents-python/tree/main/examples/tools)*

Before running these examples, be sure to review the [prerequisites and background on the integration](../README.md).

## Setup

### Knowledge Base Setup (Required for File Search)
Create a vector store with sample documents for file search testing:
```bash
uv run openai_agents/tools/setup_knowledge_base.py
```

This script:
- Creates 6 sample documents
- Uploads files to OpenAI with proper cleanup using context managers
- Creates an assistant with vector store for file search capabilities
- Updates workflow files with the new vector store ID automatically

## Running the Examples

First, start the worker (supports all tools):
```bash
uv run openai_agents/tools/run_worker.py
```

Then run individual examples in separate terminals:

### Code Interpreter
Execute Python code for mathematical calculations and data analysis:
```bash
uv run openai_agents/tools/run_code_interpreter_workflow.py
```

### File Search
Search through uploaded documents using vector similarity:
```bash
uv run openai_agents/tools/run_file_search_workflow.py
```

### Image Generation
Generate images:
```bash
uv run openai_agents/tools/run_image_generator_workflow.py
```

### Web Search
Search the web for current information with location context:
```bash
uv run openai_agents/tools/run_web_search_workflow.py
```


## Omitted Examples

The following tools from the [reference repository](https://github.com/openai/openai-agents-python/tree/main/examples/tools) are not included in this Temporal adaptation:

- **Computer Use**: Complex browser automation not suitable for distributed systems implementation.