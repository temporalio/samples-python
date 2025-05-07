import argparse
import asyncio
from ftplib import print_line

from temporalio.client import Client, WorkflowQueryRejectedError, WorkflowUpdateFailedError
from temporalio.common import WorkflowIDReusePolicy, QueryRejectCondition
from temporalio.service import RPCError, RPCStatusCode

from openai_agents.adapters.open_ai_converter import open_ai_data_converter
from openai_agents.workflows.customer_service_workflow import CustomerServiceWorkflow, ProcessUserMessageInput


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--conversation-id', type=str, required=True)
    args = parser.parse_args()

    # Create client connected to server at the given address
    client = await Client.connect("localhost:7233", data_converter=open_ai_data_converter)

    handle = client.get_workflow_handle(args.conversation_id)

    # Query the workflow for the chat history
    # If the workflow is not open, start a new one
    start = False
    try:
        history = await handle.query(CustomerServiceWorkflow.get_chat_history,
                                     reject_condition=QueryRejectCondition.NOT_OPEN)
    except WorkflowQueryRejectedError as e:
        start = True
    except RPCError as e:
        if e.status == RPCStatusCode.NOT_FOUND:
            start = True
        else:
            raise e
    if start:
        await client.start_workflow(CustomerServiceWorkflow.run,
                                    id=args.conversation_id, task_queue="my-task-queue",
                                    id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE)
        history = []
    print(*history, sep="\n")

    # Loop to send messages to the workflow
    while True:
        user_input = input("Enter your message: ")
        message_input = ProcessUserMessageInput(user_input=user_input, chat_length=len(history))
        try:
            new_history = await handle.execute_update(CustomerServiceWorkflow.process_user_message, message_input)
            history.extend(new_history)
            print(*new_history, sep="\n")
        except WorkflowUpdateFailedError:
            print_line("** Stale conversation. Reloading...")
            length = len(history)
            history = await handle.query(CustomerServiceWorkflow.get_chat_history,
                                         reject_condition=QueryRejectCondition.NOT_OPEN)
            print(*history[length:], sep="\n")


if __name__ == "__main__":
    asyncio.run(main())
