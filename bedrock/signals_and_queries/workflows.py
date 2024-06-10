import asyncio
from collections import deque
from datetime import timedelta
from typing import Deque, List, Optional, Tuple

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from bedrock.shared.activities import BedrockActivities


@workflow.defn
class SignalQueryBedrockWorkflow:
    def __init__(self) -> None:
        # List to store prompt history
        self.conversation_history: List[Tuple[str, str]] = []
        self.prompt_queue: Deque[str] = deque()
        self.conversation_summary = ""
        self.chat_timeout: bool = False

    @workflow.run
    async def run(self, inactivity_timeout_minutes: int) -> str:
        while True:
            workflow.logger.info(
                "Waiting for prompts... or closing chat after "
                + f"{inactivity_timeout_minutes} minute(s)"
            )

            # Wait for a chat message (signal) or timeout
            try:
                await workflow.wait_condition(
                    lambda: bool(self.prompt_queue),
                    timeout=timedelta(minutes=inactivity_timeout_minutes),
                )
            # If timeout was reached
            except asyncio.TimeoutError:
                self.chat_timeout = True
                workflow.logger.info("Chat closed due to inactivity")
                # End the workflow
                break

            while self.prompt_queue:
                # Fetch next user prompt and add to conversation history
                prompt = self.prompt_queue.popleft()
                self.conversation_history.append(("user", prompt))

                workflow.logger.info(f"Prompt: {prompt}")

                # Send the prompt to Amazon Bedrock
                response = await workflow.execute_activity_method(
                    BedrockActivities.prompt_bedrock,
                    self.prompt_with_history(prompt),
                    schedule_to_close_timeout=timedelta(seconds=20),
                )

                workflow.logger.info(f"{response}")

                # Append the response to the conversation history
                self.conversation_history.append(("response", response))

        # Generate a summary before ending the workflow
        self.conversation_summary = await workflow.start_activity_method(
            BedrockActivities.prompt_bedrock,
            self.prompt_summary_from_history(),
            schedule_to_close_timeout=timedelta(seconds=20),
        )

        workflow.logger.info(f"Conversation summary:\n{self.conversation_summary}")

        return f"{self.conversation_history}"

    @workflow.signal
    async def user_prompt(self, prompt: str) -> None:
        # Chat timed out but the workflow is waiting for a chat summary to be generated
        if self.chat_timeout:
            workflow.logger.warn(f"Message dropped due to chat closed: {prompt}")
            return

        self.prompt_queue.append(prompt)

    @workflow.query
    def get_conversation_history(self) -> List[Tuple[str, str]]:
        return self.conversation_history

    @workflow.query
    def get_summary_from_history(self) -> str:
        return self.conversation_summary

    # Helper method used in prompts to Amazon Bedrock
    def format_history(self) -> str:
        return " ".join(f"{text}" for _, text in self.conversation_history)

    # Create the prompt given to Amazon Bedrock for each conversational turn
    def prompt_with_history(self, prompt: str) -> str:
        history_string = self.format_history()
        return (
            f"Here is the conversation history: {history_string} Please add "
            + "a few sentence response to the prompt in plain text sentences. "
            + "Don't editorialize or add metadata like response. Keep the "
            + f"text a plain explanation based on the history. Prompt: {prompt}"
        )

    # Create the prompt to Amazon Bedrock to summarize the conversation history
    def prompt_summary_from_history(self) -> str:
        history_string = self.format_history()
        return (
            "Here is the conversation history between a user and a chatbot: "
            + f"{history_string}  -- Please produce a two sentence summary of "
            + "this conversation."
        )
