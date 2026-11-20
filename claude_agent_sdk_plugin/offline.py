from __future__ import annotations

import contextlib
import json
import os
import tempfile
import threading
import uuid
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Union

# Outlives the Worker, so a restarted Worker finds the sessions it can resume.
OFFLINE_CONFIG_DIR = os.path.join(tempfile.gettempdir(), "claude-agent-sdk-samples")


@dataclass(frozen=True)
class ApiError:
    """An error response from the Anthropic API, such as a rejected API key."""

    status: int
    type: str
    message: str

    def body(self) -> bytes:
        error = {"type": self.type, "message": self.message}
        return json.dumps({"type": "error", "error": error}).encode()


Answer = Union[
    str, list[str], dict[str, Any], ApiError, Callable[[dict[str, Any]], Any]
]


def tool_use(id: str, name: str, **tool_input: Any) -> dict[str, Any]:
    return {"type": "tool_use", "id": id, "name": name, "input": tool_input}


class ScriptedApi:
    def __init__(self, answers: Mapping[str, Answer]) -> None:
        self.answers = dict(answers)
        self.requests: list[dict[str, Any]] = []
        self.asked: list[str] = []
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_address[1]}"

    def answer(self, body: dict[str, Any]) -> Any:
        self.requests.append(body)
        prompt = prompt_of(body)
        key = next((k for k in self.answers if k in prompt), None)
        if key is None:
            return ""
        self.asked.append(key)
        answer = self.answers[key]
        return answer(body) if callable(answer) else answer

    def _handler(self) -> type[BaseHTTPRequestHandler]:
        api = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                answer = api.answer(body)
                if isinstance(answer, ApiError):
                    status, content_type = answer.status, "application/json"
                    data = answer.body()
                else:
                    status, content_type = 200, "text/event-stream"
                    data = stream(answer, body.get("model", "claude"))
                with contextlib.suppress(OSError):
                    self.send_response(status)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)

            def log_message(self, format: str, *args: Any) -> None:
                pass

        return Handler


@contextlib.contextmanager
def scripted_api(answers: Mapping[str, Answer]) -> Iterator[ScriptedApi]:
    api = ScriptedApi(answers)
    threading.Thread(target=api._server.serve_forever, daemon=True).start()
    env = {
        "ANTHROPIC_API_KEY": "offline",
        "ANTHROPIC_BASE_URL": api.url,
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        # The scripted API answers at once, so an error it returns is final.
        "CLAUDE_CODE_MAX_RETRIES": "0",
        "CLAUDE_CONFIG_DIR": OFFLINE_CONFIG_DIR,
    }
    inherited = [
        name
        for name in os.environ
        if name == "CLAUDECODE" or name.startswith("CLAUDE_CODE_")
    ]
    saved = {name: os.environ.get(name) for name in [*inherited, *env]}
    for name in inherited:
        del os.environ[name]
    os.environ.update(env)
    try:
        yield api
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        api._server.shutdown()
        api._server.server_close()


@contextlib.contextmanager
def offline_api_without_key(answers: Mapping[str, Answer]) -> Iterator[None]:
    if os.environ.get("ANTHROPIC_API_KEY"):
        yield
        return

    print("No ANTHROPIC_API_KEY, so running offline against a scripted Anthropic API.")
    with scripted_api(answers):
        yield


def prompt_of(body: dict[str, Any]) -> str:
    content = next(
        m["content"] for m in reversed(body["messages"]) if m["role"] == "user"
    )
    if isinstance(content, str):
        return content
    return " ".join(
        block.get("text") or f"tool_result:{block.get('tool_use_id')}"
        for block in content
    )


def stream(answer: Any, model: str = "claude") -> bytes:
    message = {
        "id": f"msg_{uuid.uuid4().hex}",
        "type": "message",
        "model": model,
        "role": "assistant",
        "content": [],
        "usage": {"input_tokens": 1},
    }
    events: list[dict[str, Any]] = [{"type": "message_start", "message": message}]
    if isinstance(answer, dict):
        events += [
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {**answer, "input": {}},
            },
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {
                    "type": "input_json_delta",
                    "partial_json": json.dumps(answer["input"]),
                },
            },
        ]
        stop_reason = "tool_use"
    else:
        chunks = answer if isinstance(answer, list) else [answer]
        events.append(
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text", "text": ""},
            }
        )
        events += [
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": chunk},
            }
            for chunk in chunks
        ]
        stop_reason = "end_turn"
    events += [
        {"type": "content_block_stop", "index": 0},
        {
            "type": "message_delta",
            "delta": {"stop_reason": stop_reason},
            "usage": {"output_tokens": 1},
        },
        {"type": "message_stop"},
    ]
    return "".join(
        f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events
    ).encode()
