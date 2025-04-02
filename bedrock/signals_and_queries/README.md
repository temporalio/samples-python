# Amazon Bedrock workflow using Signals and Queries

Adding signals & queries to the [basic Bedrock sample](../1_basic). Starts a workflow with a prompt, allows follow-up prompts to be given using Temporal signals, and allows the conversation history to be queried using Temporal queries.

To run, first see `samples-python` [README.md](../../README.md), and `bedrock` [README.md](../README.md) for prerequisites specific to this sample. Once set up, run the following from this directory:

1. Run the worker: `uv run run_worker.py`
2. In another terminal run the client with a prompt.

    Example: `uv run send_message.py 'What animals are marsupials?'`

3. View the worker's output for the response.
4. Give followup prompts by signaling the workflow.

    Example: `uv run send_message.py 'Do they lay eggs?'`
5. Get the conversation history by querying the workflow.
    
    Example: `uv run get_history.py`
6. The workflow will timeout after inactivity.
