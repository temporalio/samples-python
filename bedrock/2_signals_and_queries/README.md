# 2_SignalsAndQueries
Adding signals & queries. Starts a workflow with a prompt, allows follow-up prompts to be given using Temporal signals, and allows the conversation history to be queried using Temporal queries.

1. Run the worker: `python run_worker.py`
2. In another terminal run the client with a prompt.

    Example: `python send_message.py 'What animals are marsupials?'`

3. View the worker's output for the response.
4. Give followup prompts by signaling the workflow.

    Example: `python send_message.py 'Do they lay eggs?'`
5. Get the conversation history by querying the workflow.
    
    Example: `python get_history.py`
6. The workflow will timeout after inactivity.
