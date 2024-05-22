import asyncio
from datetime import timedelta
from temporalio import workflow
from collections import deque
from typing import List, Tuple, Deque, Optional

with workflow.unsafe.imports_passed_through():
    from activities import prompt_bedrock


@workflow.defn
class SignalQueryBedrockWorkflow:
    def __init__(self) -> None:
        self.conversation_history: List[Tuple[str, str]] = (
            []
        )  # List to store prompt history
        self.prompt_queue: Deque[str] = deque()
        self.conversation_summary: str = ""

    @workflow.run
    async def run(self, inactivity_timeout_minutes: int) -> str:

        while True:
            try:
                workflow.logger.info(
                    f"\nWaiting for prompts... or closing chat after "
                    + "%d minute(s)" % inactivity_timeout_minutes
                )

                # Wait for a chat message (signal) or timeout
                await workflow.wait_condition(
                    lambda: bool(self.prompt_queue),
                    timeout=timedelta(minutes=inactivity_timeout_minutes),
                )

                prompt = self.prompt_queue.popleft()  # done with current prompt
                workflow.logger.info("\nPrompt: " + prompt)
                self.conversation_history.append(
                    ("user", prompt)
                )  # Log user prompt to conversation history

                # If a prompt is given, send to Amazon Bedrock
                response = await workflow.execute_activity(
                    prompt_bedrock,
                    self.prompt_with_history(prompt),
                    schedule_to_close_timeout=timedelta(seconds=20),
                )

                workflow.logger.info(response)

                # Append the response to the conversation history
                self.conversation_history.append(("response", response))

                # summarize the conversation to date using Amazon Bedrock
                # uses start_activity with a callback
                # so it doesn't block new messages being sent to Amazon Bedrock
                summary_activity_task = workflow.start_activity(
                    prompt_bedrock,
                    self.prompt_summary_from_history(),
                    schedule_to_close_timeout=timedelta(seconds=20),
                )
                summary_activity_task.add_done_callback(self.summary_complete)

            # if timeout was reached
            except asyncio.TimeoutError:
                workflow.logger.info("\n*** Chat closed due to inactivity ***")
                # ensure a summary has been generated before ending the workflow
                await workflow.wait_condition(lambda: summary_activity_task.done())
                workflow.logger.info("\nConversation summary:")
                workflow.logger.info(self.conversation_summary)
                return "{}".format(self.conversation_history)

    @workflow.signal
    async def user_prompt(self, prompt: str) -> None:
        self.prompt_queue.append(prompt)

    @workflow.query
    def get_conversation_history(self) -> List[Tuple[str, str]]:
        return self.conversation_history

    @workflow.query
    def get_summary_from_history(self) -> Optional[str]:
        return self.conversation_summary

    # helper method used in prompts to Amazon Bedrock
    def format_history(self) -> str:
        return " ".join(f"{text}" for _, text in self.conversation_history)

    # Create the prompt given to Amazon Bedrock for each conversational turn
    def prompt_with_history(self, prompt: str) -> str:
        history_string = self.format_history()
        return (
            "Here is the conversation history:"
            + history_string
            + " Please add a few sentence response to the prompt "
            + "in plain text sentences. Don't editorialize or add metadata like "
            + "response. Keep the text a plain explanation based on the history. Prompt: "
            + prompt
        )

    # Create the prompt given to Amazon Bedrock to summarize the conversation history
    def prompt_summary_from_history(self) -> str:
        history_string = self.format_history()
        return (
            "Here is the conversation history between a user and a chatbot:"
            + history_string
            + " -- Please produce a two sentence summary of this conversation."
        )

    # callback -- save the latest conversation history once generated
    def summary_complete(self, task) -> None:
        self.conversation_summary = task.result()
