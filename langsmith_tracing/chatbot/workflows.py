"""Conversational chatbot workflow with tool loop and LangSmith tracing."""

import json
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from langsmith import traceable

    from langsmith_tracing.chatbot.activities import (
        NoteRequest,
        OpenAIRequest,
        call_openai,
        read_note,
        save_note,
    )

RETRY = RetryPolicy(initial_interval=timedelta(seconds=2), maximum_attempts=3)

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
    async def user_message(self, message: str) -> None:
        self._pending_message = message

    @workflow.signal
    async def exit(self) -> None:
        self._done = True

    @workflow.query
    def last_response(self) -> str:
        return self._last_response

    @workflow.query
    def notes(self) -> dict[str, str]:
        return dict(self._notes)

    # Do not put @traceable directly on the @workflow.run method — it would
    # violate replay safety. Instead, wrap an inner function.
    @workflow.run
    async def run(self) -> str:
        now = workflow.now().strftime("%b %d %H:%M")
        return await traceable(
            name=f"Session {now}",
            run_type="chain",
            metadata={"workflow_id": workflow.info().workflow_id},
            tags=["chatbot-session"],
        )(self._session)()

    async def _session(self) -> str:
        while not self._done:
            await workflow.wait_condition(
                lambda: self._pending_message is not None or self._done
            )
            if self._done:
                break
            message = self._pending_message
            self._pending_message = None
            self._last_response = await self._query_openai(message)

        return "Session ended."

    async def _query_openai(self, message: str | None) -> str:
        @traceable(
            name=f"Request: {(message or '')[:60]}",
            run_type="chain",
            tags=["user-message"],
        )
        async def _traced():
            input_for_next: str | list = message or ""
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
                    retry_policy=RETRY,
                )
                self._previous_response_id = response.id

                tool_results = []
                for item in response.output:
                    if item.type != "function_call":
                        continue
                    args = json.loads(item.arguments)
                    if item.name == "save_note":
                        self._notes[args["name"]] = args["content"]
                        result = await workflow.execute_activity(
                            save_note,
                            NoteRequest(name=args["name"], content=args["content"]),
                            start_to_close_timeout=timedelta(seconds=10),
                            retry_policy=RETRY,
                        )
                        tool_results.append(
                            {
                                "type": "function_call_output",
                                "call_id": item.call_id,
                                "output": result,
                            }
                        )
                    elif item.name == "read_note":
                        content = self._notes.get(args["name"], "Note not found.")
                        result = await workflow.execute_activity(
                            read_note,
                            NoteRequest(name=args["name"], content=content),
                            start_to_close_timeout=timedelta(seconds=10),
                            retry_policy=RETRY,
                        )
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
