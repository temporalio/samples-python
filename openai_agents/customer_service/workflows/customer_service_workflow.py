from __future__ import annotations as _annotations

from agents import (
    HandoffCallItem,
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
from pydantic import dataclasses
from temporalio import workflow

from openai_agents.customer_service.customer_service import (
    AirlineAgentContext,
    ProcessUserMessageInput,
    init_agents,
)


@dataclasses.dataclass
class CustomerServiceWorkflowState:
    printed_history: list[str]
    current_agent_name: str
    context: AirlineAgentContext
    input_items: list[TResponseInputItem]


@workflow.defn
class CustomerServiceWorkflow:
    @workflow.init
    def __init__(
        self, customer_service_state: CustomerServiceWorkflowState | None = None
    ):
        self.run_config = RunConfig()

        starting_agent, self.agent_map = init_agents()
        self.current_agent = (
            self.agent_map[customer_service_state.current_agent_name]
            if customer_service_state
            else starting_agent
        )
        self.context = (
            customer_service_state.context
            if customer_service_state
            else AirlineAgentContext()
        )
        self.printed_history: list[str] = (
            customer_service_state.printed_history if customer_service_state else []
        )
        self.input_items = (
            customer_service_state.input_items if customer_service_state else []
        )

    @workflow.run
    async def run(
        self, customer_service_state: CustomerServiceWorkflowState | None = None
    ):
        await workflow.wait_condition(
            lambda: workflow.info().is_continue_as_new_suggested()
            and workflow.all_handlers_finished()
        )
        workflow.continue_as_new(
            CustomerServiceWorkflowState(
                printed_history=self.printed_history,
                current_agent_name=self.current_agent.name,
                context=self.context,
                input_items=self.input_items,
            )
        )

    @workflow.query
    def get_chat_history(self) -> list[str]:
        return self.printed_history

    @workflow.update
    async def process_user_message(self, input: ProcessUserMessageInput) -> list[str]:
        length = len(self.printed_history)
        self.printed_history.append(f"User: {input.user_input}")
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
                    self.printed_history.append(
                        f"{agent_name}: {ItemHelpers.text_message_output(new_item)}"
                    )
                elif isinstance(new_item, HandoffOutputItem):
                    self.printed_history.append(
                        f"Handed off from {new_item.source_agent.name} to {new_item.target_agent.name}"
                    )
                elif isinstance(new_item, HandoffCallItem):
                    self.printed_history.append(
                        f"{agent_name}: Handed off to tool {new_item.raw_item.name}"
                    )
                elif isinstance(new_item, ToolCallItem):
                    self.printed_history.append(f"{agent_name}: Calling a tool")
                elif isinstance(new_item, ToolCallOutputItem):
                    self.printed_history.append(
                        f"{agent_name}: Tool call output: {new_item.output}"
                    )
                else:
                    self.printed_history.append(
                        f"{agent_name}: Skipping item: {new_item.__class__.__name__}"
                    )
            self.input_items = result.to_input_list()
            self.current_agent = result.last_agent
        workflow.set_current_details("\n\n".join(self.printed_history))

        return self.printed_history[length:]

    @process_user_message.validator
    def validate_process_user_message(self, input: ProcessUserMessageInput) -> None:
        if not input.user_input:
            raise ValueError("User input cannot be empty.")
        if len(input.user_input) > 1000:
            raise ValueError("User input is too long. Please limit to 1000 characters.")
        if input.chat_length != len(self.printed_history):
            raise ValueError("Stale chat history. Please refresh the chat.")
