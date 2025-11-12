"""
Entity workflow for the Greeting service.

This workflow follows the entity pattern: it runs indefinitely, processing operations
(signals, updates, queries) as they arrive. It periodically continues-as-new to prevent
history from growing too large.
"""

import asyncio
from dataclasses import dataclass
from datetime import timedelta
from typing import Dict, List, Optional

from temporalio import workflow
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    from message_passing.introduction import Language
    from message_passing.introduction.activities import call_greeting_service
    from message_passing.introduction.workflows import (
        ApproveInput,
        GetLanguagesInput,
        SetLanguageInput,
    )


@dataclass
class GreetingEntityState:
    """State that persists across continue-as-new operations."""
    greetings: Dict[Language, str]
    language: Language
    approver_name: Optional[str] = None


@dataclass
class GreetingEntityInput:
    """Input for the entity workflow, used for continue-as-new."""
    state: Optional[GreetingEntityState] = None


@workflow.defn
class GreetingEntityWorkflow:
    """
    An entity workflow that manages greeting state and processes operations.

    This workflow follows the entity pattern:
    - Runs indefinitely in a loop
    - Processes signals and updates as they arrive
    - Supports queries at any time
    - Periodically continues-as-new to prevent history growth
    """

    @workflow.init
    def init(self, input: Optional[GreetingEntityInput] = None) -> None:
        """Initialize workflow state, restoring from continue-as-new if provided."""
        if input and input.state:
            self.greetings = input.state.greetings.copy()
            self.language = input.state.language
            self.approver_name = input.state.approver_name
        else:
            # Initial state
            self.greetings = {
                Language.CHINESE: "你好，世界",
                Language.ENGLISH: "Hello, world",
            }
            self.language = Language.ENGLISH
            self.approver_name = None
        
        # Lock to protect state during async operations
        self.lock = asyncio.Lock()

    @workflow.run
    async def run(self, input: Optional[GreetingEntityInput] = None) -> None:
        """
        Main entity workflow loop. Runs indefinitely, processing operations.

        The workflow:
        1. Waits for operations (signals/updates) to arrive
        2. Processes them via their handlers
        3. Periodically continues-as-new to prevent history growth
        
        Note: State is initialized in @workflow.init. When continuing as new,
        init is called again with the new input containing the state.
        """
        # Main entity loop - runs indefinitely
        # Entity workflows process operations (signals/updates) via their handlers.
        # The main loop periodically checks if we should continue-as-new to prevent
        # history from growing too large.
        while True:
            # Wait for a timeout, then check if we should continue as new
            # Signals and updates are handled by their respective handlers
            try:
                # Use a dummy condition that will timeout, allowing us to periodically
                # check for continue-as-new
                await workflow.wait_condition(
                    lambda: False,  # Never true, just wait for timeout
                    timeout=timedelta(minutes=10),  # Check every 10 minutes
                )
            except asyncio.TimeoutError:
                # Timeout reached - check if we should continue as new
                if self._should_continue_as_new():
                    # Wait for all handlers (signals/updates) to finish before continuing as new
                    # This ensures no operations are in progress when we checkpoint state
                    await workflow.wait_condition(lambda: workflow.all_handlers_finished())
                    
                    workflow.logger.info("Continuing as new to prevent history growth")
                    
                    # Continue as new with current state
                    workflow.continue_as_new(
                        GreetingEntityInput(
                            state=GreetingEntityState(
                                greetings=self.greetings.copy(),
                                language=self.language,
                                approver_name=self.approver_name,
                            )
                        )
                    )

    def _should_continue_as_new(self) -> bool:
        """Check if workflow should continue as new."""
        # Use Temporal's suggestion if available
        if workflow.info().is_continue_as_new_suggested():
            return True
        # For testing/demo: continue as new if history gets large
        # In production, rely on Temporal's suggestion
        if workflow.info().get_current_history_length() > 1000:
            return True
        return False

    @workflow.query
    def get_languages(self, input: GetLanguagesInput) -> List[Language]:
        """
        Query: Get list of supported languages.
        
        Returns all languages if include_unsupported is True,
        otherwise returns only languages with greetings defined.
        """
        if input.include_unsupported:
            return sorted(Language)
        else:
            return sorted(self.greetings.keys())

    @workflow.query
    def get_language(self) -> Language:
        """Query: Get the current language."""
        return self.language

    @workflow.signal
    def approve(self, input: ApproveInput) -> None:
        """
        Signal: Record approval.
        
        Signals mutate state but don't return values.
        This is processed asynchronously by the entity loop.
        """
        self.approver_name = input.name
        workflow.logger.info(f"Approved by: {input.name}")

    @workflow.update
    def set_language(self, input: SetLanguageInput) -> Language:
        """
        Update: Set the language synchronously (no activity).
        
        Updates can mutate state and return values.
        This update handler is synchronous and only modifies local state.
        """
        if input.language not in self.greetings:
            raise ValueError(f"{input.language.name} is not supported")
        
        previous_language = self.language
        self.language = input.language
        return previous_language

    @set_language.validator
    def validate_language(self, input: SetLanguageInput) -> None:
        """Validator: Reject unsupported languages before update is accepted."""
        if input.language not in self.greetings:
            raise ValueError(f"{input.language.name} is not supported")

    @workflow.update
    async def set_language_using_activity(self, input: SetLanguageInput) -> Language:
        """
        Update: Set the language using an activity to fetch greeting.
        
        This update handler is async and can execute activities.
        It uses a lock to ensure sequential processing of multiple updates.
        """
        previous_language = self.language
        
        # If language not in greetings, fetch it via activity
        if input.language not in self.greetings:
            # Use lock to ensure sequential processing
            async with self.lock:
                greeting = await workflow.execute_activity(
                    call_greeting_service,
                    input.language,
                    start_to_close_timeout=timedelta(seconds=10),
                )
                
                if greeting is None:
                    raise ApplicationError(
                        f"Greeting service does not support {input.language.name}"
                    )
                
                self.greetings[input.language] = greeting
        
        self.language = input.language
        return previous_language

