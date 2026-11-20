import os
import threading
from typing import Any, Literal

from bedrock_agentcore.tools.code_interpreter_client import (
    DEFAULT_IDENTIFIER,
    CodeInterpreter,
)
from temporalio import activity

# Code Interpreter clients by session name (the Workflow ID). Activity sessions
# keep every execute_code of a Workflow on this Worker, so an in-process cache
# finds the sandbox again; a fresh process falls back to looking it up by name.
_interpreters: dict[str, CodeInterpreter] = {}
_lock = threading.Lock()


def _interpreter_for(session_name: str) -> CodeInterpreter:
    """Return a client bound to the READY sandbox named ``session_name``, starting one if needed."""
    with _lock:
        interpreter = _interpreters.get(session_name)
        if interpreter is None:
            interpreter = CodeInterpreter(
                region=os.environ.get("AWS_REGION", "us-west-2")
            )
            identifier = os.environ.get(
                "CODE_INTERPRETER_IDENTIFIER", DEFAULT_IDENTIFIER
            )
            session_id = _find_ready_session(interpreter, identifier, session_name)
            if session_id:
                interpreter.identifier = identifier
                interpreter.session_id = session_id
            else:
                interpreter.start(identifier=identifier, name=session_name)
            _interpreters[session_name] = interpreter
        return interpreter


def _find_ready_session(
    interpreter: CodeInterpreter, identifier: str, session_name: str
) -> str | None:
    """The ID of a READY sandbox session named ``session_name``, if one exists."""
    next_token = None
    while True:
        page = interpreter.list_sessions(
            interpreter_id=identifier,
            status="READY",
            max_results=100,
            next_token=next_token,
        )
        for item in page.get("items", []):
            if item.get("name") == session_name:
                return item["sessionId"]
        next_token = page.get("nextToken")
        if not next_token:
            return None


# @@@SNIPSTART python-agentcore-openai-code-interpreter-activity
# Use AgentCore Code Interpreter to provide a code sandbox and execute LLM generated solution
@activity.defn
def execute_code(
    code: str, language: Literal["python", "javascript", "typescript"] = "python"
) -> dict[str, Any]:
    """Run code in this Session's sandbox (workflow ID) and return the Code Interpreter result."""
    info = activity.info()
    session_name = info.workflow_id or info.activity_id
    interpreter = _interpreter_for(session_name)
    try:
        response = interpreter.execute_code(code, language=language)
    except Exception:
        # e.g. the sandbox timed out; start over with a fresh one on retry.
        with _lock:
            _interpreters.pop(session_name, None)
        raise
    # The response streams events; the "result" event holds the JSON-serializable
    # outcome (content, structuredContent with stdout/stderr, isError).
    for event in response["stream"]:
        if "result" in event:
            return event["result"]
    return {"isError": True, "content": [{"type": "text", "text": "no result"}]}


# @@@SNIPEND
