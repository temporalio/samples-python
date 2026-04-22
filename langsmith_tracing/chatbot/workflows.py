"""Conversational chatbot workflow with tool loop and LangSmith tracing."""

import json
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from langsmith import traceable

    from langsmith_tracing.chatbot.activities import OpenAIRequest, call_openai

TOOLS = [
    {
        "type": "function",
        "name": "save_note",
        "description": "Save or update a note.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name/key for the note."},
                "content": {
                    "type": "string",
                    "description": "Content of the note.",
                },
            },
            "required": ["name", "content"],
        },
    },
    {
        "type": "function",
        "name": "read_note",
        "description": "Read a previously saved note.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name/key of the note to read.",
                },
            },
            "required": ["name"],
        },
    },
]


@workflow.defn
class ChatbotWorkflow:
    def __init__(self):
        self._pending_message: str | None = None
        self._last_response: str = ""
        self._previous_response_id: str | None = None
        self._notes: dict[str, str] = {}
        self._done = False

    @workflow.signal
    async def exit(self) -> None:
        self._done = True

    @workflow.query
    def notes(self) -> dict[str, str]:
        return dict(self._notes)

    @workflow.update
    async def message_from_user(self, message: str) -> str:
        """Hand the message to the main loop and wait for its response."""

        # Inner @traceable captures the message as input and response as output.
        @traceable(name=f"Update: {message[:60]}", run_type="chain")
        async def _traced(msg: str) -> str:
            # Wait until any previous message has finished processing
            await workflow.wait_condition(lambda: self._pending_message is None)
            self._pending_message = msg
            # Main loop sets _last_response, then clears _pending_message to signal done
            await workflow.wait_condition(lambda: self._pending_message is None)
            return self._last_response

        return await _traced(message)

    # Do not decorate @workflow.run with @traceable — it would violate
    # replay safety and produce duplicate or orphaned traces. Instead,
    # wrap an inner function, eg. self._run_inner() in this case.
    @workflow.run
    async def run(self) -> str:
        # Alternative to @traceable decorator: call traceable() as a function
        # for dynamic trace names that depend on runtime values.
        now = workflow.now().strftime("%b %d %H:%M")
        return await traceable(
            name=f"Session {now}",
            run_type="chain",
            metadata={"workflow_id": workflow.info().workflow_id},
            tags=["chatbot-session"],
        )(self._run_inner)()

    async def _run_inner(self) -> str:
        while not self._done:
            await workflow.wait_condition(
                lambda: self._pending_message is not None or self._done
            )
            if self._done:
                break
            assert self._pending_message is not None
            message = self._pending_message
            self._last_response = await self._query_openai(message)
            # Clear pending_message AFTER setting the response so the update
            # handler reads the correct response when its wait_condition fires.
            self._pending_message = None

        return "Session ended."

    # Unlike @workflow.run, other workflow methods can be decorated with
    # @traceable directly — they run inside the plugin-managed context
    # where trace I/O is handled safely during replay.
    @traceable(name="Save Note", run_type="tool")
    def _save_note(self, name: str, content: str) -> str:
        self._notes[name] = content
        return f"Saved note '{name}'."

    @traceable(name="Read Note", run_type="tool")
    def _read_note(self, name: str) -> str:
        return self._notes.get(name, "Note not found.")

    async def _query_openai(self, message: str) -> str:
        @traceable(
            name=f"Request: {message[:60]}",
            run_type="chain",
            tags=["user-message"],
        )
        async def _traced():
            input_for_next: str | list = message
            while True:
                response = await workflow.execute_activity(
                    call_openai,
                    OpenAIRequest(
                        model="gpt-4o-mini",
                        input=input_for_next,
                        tools=TOOLS,
                        previous_response_id=self._previous_response_id,
                    ),
                    start_to_close_timeout=timedelta(seconds=60),
                    retry_policy=RetryPolicy(
                        initial_interval=timedelta(seconds=2), maximum_attempts=3
                    ),
                )
                self._previous_response_id = response.id

                tool_results = []
                for item in response.output:
                    if item.type != "function_call":
                        continue
                    args = json.loads(item.arguments)
                    if item.name == "save_note":
                        result = self._save_note(args["name"], args["content"])
                        tool_results.append(
                            {
                                "type": "function_call_output",
                                "call_id": item.call_id,
                                "output": result,
                            }
                        )
                    elif item.name == "read_note":
                        result = self._read_note(args["name"])
                        tool_results.append(
                            {
                                "type": "function_call_output",
                                "call_id": item.call_id,
                                "output": result,
                            }
                        )

                if not tool_results:
                    return response.output_text or "Done."

                input_for_next = tool_results

        return await _traced()
