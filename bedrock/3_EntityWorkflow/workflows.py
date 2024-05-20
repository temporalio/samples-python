import asyncio
from datetime import timedelta
from temporalio import workflow

from collections import deque

with workflow.unsafe.imports_passed_through():
    from activities import prompt_bedrock


@workflow.defn
class EntityBedrockWorkflow:
    def __init__(self) -> None:
        self.conversation_history = []  # List to store prompt history
        self.prompt_queue = deque()
        self.conversation_summary = None
        self.continue_as_new_per_turns = 6 
        self.end_chat = False

    @workflow.run
    async def run(
        self,
        conversation_summary: str = None,
        prompt_queue: deque = None,
    ) -> str:

        if conversation_summary:
            self.conversation_history.append(
                ("conversation_summary", conversation_summary)
            )

        if prompt_queue:
            self.prompt_queue = prompt_queue

        summary_activity_task = None

        while True:
            workflow.logger.info(f"\nWaiting for prompts...")

            # Wait for a chat message (signal) or timeout
            await workflow.wait_condition(lambda: self.prompt_queue or self.end_chat)

            # if end chat signal was sent
            if self.end_chat:
                # the workflow might be continued as new without any chat to summarize
                if summary_activity_task:
                    # ensure conversation summary task has finished
                    # before closing the workflow (avoid race)
                    await workflow.wait_condition(lambda: summary_activity_task.done())
                else:
                    # conversation history from previous workflow
                    self.conversation_summary = conversation_summary
                workflow.logger.info("\nChat ended. Conversation summary:")
                workflow.logger.info(self.conversation_summary)
                return "{}".format(self.conversation_history)

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

            # Continue as new every x conversational turns to avoid event history
            # size getting too large
            # This is also to avoid the prompt (with conversational history)
            # getting too large for AWS Bedrock
            # We summarize the chat to date and use that as input to the new workflow
            if len(self.conversation_history) >= self.continue_as_new_per_turns:
                # ensure conversation summary task has finished
                # before continuing as new
                await workflow.wait_condition(lambda: summary_activity_task.done())
                workflow.logger.info(
                    "Continuing as new due to %i conversational turns."
                    % self.continue_as_new_per_turns,
                )
                workflow.continue_as_new(
                    args=[
                        self.conversation_summary,
                        self.prompt_queue,
                    ]
                )

    @workflow.signal
    async def user_prompt(self, prompt: str) -> None:
        self.prompt_queue.append(prompt)

    @workflow.signal
    async def end_chat(self) -> None:
        self.end_chat = True

    @workflow.query
    def conversation_history(self) -> list:
        return self.conversation_history

    @workflow.query
    def summary_from_history(self) -> str:
        return self.conversation_summary

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

    # Create the prompt given to Amazon Bedrock to summarize the conversation history
    def prompt_summary_from_history(self):
        history_string = self.format_history()
        return (
            "Here is the conversation history between a user and a chatbot:"
            + history_string
            + " -- Please produce a two sentence summary of this conversation."
        )

    # callback -- save the latest conversation history once generated
    def summary_complete(self, task):
        self.conversation_summary = task.result()
