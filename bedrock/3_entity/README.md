# 3_EntityWorkflow
Multi-Turn Chat using an Entity Workflow. The workflow runs forever unless explicitly ended. The workflow continues as new after a configurable number of chat turns to keep the prompt size small and the Temporal event history small. Each continued-as-new workflow receives a summary of the conversation history so far for context.

1. Run the worker: `python run_worker.py`
2. In another terminal run the client with a prompt.

    Example: `python send_message.py 'What animals are marsupials?'`

3. View the worker's output for the response.
4. Give followup prompts by signaling the workflow.

    Example: `python send_message.py 'Do they lay eggs?'`
5. Get the conversation history summary by querying the workflow.
    
    Example: `python get_history.py`
6. To end the chat session, run `python end_chat.py`
