# Basic Amazon Bedrock workflow

A basic Bedrock workflow. Starts a workflow with a prompt, generates a response and ends the workflow.

To run, first see `samples-python` [README.md](../../README.md), and `bedrock` [README.md](../README.md) for prerequisites specific to this sample. Once set up, run the following from this directory:

1. Run the worker: `uv run run_worker.py`
2. In another terminal run the client with a prompt:

    e.g. `uv run send_message.py 'What animals are marsupials?'`