from __future__ import annotations as _annotations

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from agents import (
        Agent,
        HandoffOutputItem,
        ItemHelpers,
        MessageOutputItem,
        RunConfig,
        Runner,
        ToolCallItem,
        ToolCallOutputItem,
        TResponseInputItem,
        trace,
    )

    from openai_agents.workflows.customer_service import (
        AirlineAgentContext,
        ProcessUserMessageInput,
        init_agents,
    )


@workflow.defn
class CustomerServiceWorkflow:
    @workflow.init
    def __init__(self, input_items: list[TResponseInputItem] | None = None):
        self.run_config = RunConfig()
        self.chat_history: list[str] = []
        self.current_agent: Agent[AirlineAgentContext] = init_agents()
        self.context = AirlineAgentContext()
        self.input_items = [] if input_items is None else input_items

    @workflow.run
    async def run(self, input_items: list[TResponseInputItem] | None = None):
        await workflow.wait_condition(
            lambda: workflow.info().is_continue_as_new_suggested()
            and workflow.all_handlers_finished()
        )
        workflow.continue_as_new(self.input_items)

    @workflow.query
    def get_chat_history(self) -> list[str]:
        return self.chat_history

    @workflow.update
    async def process_user_message(self, input: ProcessUserMessageInput) -> list[str]:
        length = len(self.chat_history)
        self.chat_history.append(f"User: {input.user_input}")
        with trace("Customer service", group_id=workflow.info().workflow_id):
            self.input_items.append({"content": input.user_input, "role": "user"})
            result = await Runner.run(
                self.current_agent,
                self.input_items,
                context=self.context,
                run_config=self.run_config,
            )

            for new_item in result.new_items:
                agent_name = new_item.agent.name
                if isinstance(new_item, MessageOutputItem):
                    self.chat_history.append(
                        f"{agent_name}: {ItemHelpers.text_message_output(new_item)}"
                    )
                elif isinstance(new_item, HandoffOutputItem):
                    self.chat_history.append(
                        f"Handed off from {new_item.source_agent.name} to {new_item.target_agent.name}"
                    )
                elif isinstance(new_item, ToolCallItem):
                    self.chat_history.append(f"{agent_name}: Calling a tool")
                elif isinstance(new_item, ToolCallOutputItem):
                    self.chat_history.append(
                        f"{agent_name}: Tool call output: {new_item.output}"
                    )
                else:
                    self.chat_history.append(
                        f"{agent_name}: Skipping item: {new_item.__class__.__name__}"
                    )
            self.input_items = result.to_input_list()
            self.current_agent = result.last_agent
        workflow.set_current_details("\n\n".join(self.chat_history))
        return self.chat_history[length:]

    @process_user_message.validator
    def validate_process_user_message(self, input: ProcessUserMessageInput) -> None:
        if not input.user_input:
            raise ValueError("User input cannot be empty.")
        if len(input.user_input) > 1000:
            raise ValueError("User input is too long. Please limit to 1000 characters.")
        if input.chat_length != len(self.chat_history):
            raise ValueError("Stale chat history. Please refresh the chat.")
