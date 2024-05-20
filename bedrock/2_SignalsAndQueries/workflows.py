import asyncio
from datetime import timedelta
from temporalio import workflow

from collections import deque

with workflow.unsafe.imports_passed_through():
    from activities import prompt_bedrock


@workflow.defn
class SignalQueryBedrockWorkflow:
    def __init__(self) -> None:
        self.conversation_history = []  # List to store prompt history
        self.prompt_queue = deque()

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
                    lambda: self.prompt_queue,
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

            # if timeout was reached
            except asyncio.TimeoutError:
                workflow.logger.info("\n*** Chat closed due to inactivity ***")
                return "{}".format(self.conversation_history)

    @workflow.signal
    async def user_prompt(self, prompt: str) -> None:
        self.prompt_queue.append(prompt)

    @workflow.query
    def conversation_history(self) -> list:
        return self.conversation_history

    # helper method used in prompts to Amazon Bedrock
    def format_history(self):
        return " ".join(f"{text}" for type, text in self.conversation_history)

    # Create the prompt given to Amazon Bedrock for each conversational turn
    def prompt_with_history(self, prompt):
        history_string = self.format_history()
        return (
            "Here is the conversation history:"
            + history_string
            + " Please add a few sentence response to the prompt "
            + "in plain text sentences. Don't editorialize or add metadata like "
            + "response. Keep the text a plain explanation based on the history. Prompt: "
            + prompt
        )
