import asyncio
import io
import json
import os
import re
import tarfile
import uuid
from collections.abc import Mapping
from dataclasses import dataclass

from claude_agent_sdk import (
    CLIConnectionError,
    InMemorySessionStore,
    get_session_messages_from_store,
    project_key_for_directory,
)
from temporalio import activity
from temporalio.claude_agent_sdk import (
    ClaudeCodeProcess,
    ConnectActivityInput,
    Output,
    SubprocessConnector,
)

WORKSPACE = "/home/agent/workspace"
PROXY_MANAGED_KEY = "sk-ant-api03-proxy-managed"
FORWARDED_ENV = ("ANTHROPIC_BASE_URL", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC")


async def sbx(*args: str, input: bytes | None = None) -> bytes:
    process = await asyncio.create_subprocess_exec(
        "sbx",
        *args,
        stdin=asyncio.subprocess.DEVNULL if input is None else asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await process.communicate(input)
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()

    if process.returncode:
        message = stderr.decode(errors="replace").strip()
        raise RuntimeError(f"sbx {args[0]} failed: {message}")

    return stdout


def sandbox_name() -> str:
    """The sandbox of the Workflow that runs this Activity."""
    workflow_id = uuid.uuid5(uuid.NAMESPACE_URL, str(activity.info().workflow_id))
    return f"claude-sandbox-{workflow_id}"


def sandbox_env(request_env: dict[str, str]) -> dict[str, str]:
    # A loopback base URL becomes host.docker.internal, so the sandbox can reach
    # a gateway on the Worker's host.
    forwarded = {
        name: re.sub(r"//(127\.0\.0\.1|localhost)\b", "//host.docker.internal", value)
        for name in FORWARDED_ENV
        if (value := os.environ.get(name))
    }

    # Claude Code needs a key to start, so it gets a placeholder. The sandbox's
    # proxy swaps in the real key on requests to Anthropic.
    return {
        "ANTHROPIC_API_KEY": PROXY_MANAGED_KEY,
        **forwarded,
        **request_env,
    }


def tar(directory: str) -> bytes:
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w") as tar:
        tar.add(directory, arcname=".")

    return archive.getvalue()


class SandboxConnector:
    def __init__(self, uploads: Mapping[str, str] | None = None) -> None:
        """Run Claude Code in a Docker Sandbox.

        Args:
            uploads: Directories on the Worker to copy into each sandbox, by
                their path in the sandbox.
        """
        self.uploads = dict(uploads or {})

    async def connect(self, request: ConnectActivityInput) -> ClaudeCodeProcess:
        if request.user is not None:
            raise CLIConnectionError("Claude Code runs as the sandbox's agent user")

        # One sandbox per Workflow, outliving the Worker and the Workflow, so a retried launch, or
        # a client that resumes the session after its Worker went away, finds the
        # session and the workspace in it.
        # sbx keeps sandboxes on the machine that runs it, so a resume only finds
        # it on the same machine. With Workers on several machines, pass
        # activity_options={"connect": {"task_queue": ...}} with a task queue
        # only one machine polls.
        name = sandbox_name()
        if name not in (await sbx("ls", "-q")).decode().split():
            await sbx("create", "--name", name, "--no-progress", "claude")

        # "**" also reaches every port on the Worker's host through
        # host.docker.internal. Narrow it if that host runs services the agent
        # shouldn't reach.
        await sbx("policy", "allow", "network", "--sandbox", name, "**")

        # Register the key as the sandbox's "anthropic" service secret. The
        # sandbox's egress proxy injects it into outbound requests to Anthropic's
        # API hosts, so the key never enters the sandbox. Requests to any other
        # host, such as a custom ANTHROPIC_BASE_URL, go out without it.
        if key := os.environ.get("ANTHROPIC_API_KEY"):
            await sbx(
                "secret",
                "set",
                "anthropic",
                "--sandbox",
                name,
                "--force",
                input=key.encode(),
            )

        for path, directory in self.uploads.items():
            script = 'mkdir -p "$1" && tar -x -C "$1"'
            await sbx(
                "exec", "-i", name, "sh", "-c", script, "sh", path, input=tar(directory)
            )

        env_flags = [
            flag
            for key, value in sandbox_env(request.env).items()
            for flag in ("-e", f"{key}={value}")
        ]

        process = await SubprocessConnector().connect(
            ConnectActivityInput(
                cli_path="sbx",
                args=[
                    "exec",
                    "-i",
                    *env_flags,
                    "-w",
                    request.cwd or WORKSPACE,
                    name,
                    request.cli_path or "claude",
                    *request.args,
                ],
                env={},
                max_buffer_size=request.max_buffer_size,
            )
        )
        return SandboxProcess(name, process)


class SandboxProcess:
    """Claude Code in a sandbox, reached through ``sbx exec``."""

    def __init__(self, name: str, process: ClaudeCodeProcess) -> None:
        self.name = name
        self.process = process

    async def write(self, data: str) -> None:
        await self.process.write(data)

    async def end_input(self) -> None:
        await self.process.end_input()

    async def read(self) -> list[Output]:
        return await self.process.read()

    async def close(self) -> None:
        await self.process.close()

    async def terminate(self) -> None:
        # The Worker connected to this sandbox is shutting down. Stop Claude Code
        # as SIGTERM does, so a resumed session continues its turn.
        await sbx("exec", self.name, "pkill", "-TERM", "-x", "claude")


@dataclass
class SavedTurn:
    started: bool  # Claude Code saved the prompt
    result: str | None  # the final answer, once the turn finished


@activity.defn
async def find_saved_turn(session_id: str) -> SavedTurn:
    """Read how far the session's turn got from its transcript in the sandbox."""
    script = 'cat "$HOME"/.claude/projects/*/"$1".jsonl 2>/dev/null || true'
    transcript = await sbx("exec", sandbox_name(), "sh", "-c", script, "sh", session_id)

    # Give the transcript to the Claude Agent SDK through an in-memory store.
    # Nothing is written to the sandbox.
    store = InMemorySessionStore()
    await store.append(
        {
            "project_key": project_key_for_directory(WORKSPACE),
            "session_id": session_id,
        },
        [json.loads(line) for line in transcript.splitlines()],
    )
    messages = await get_session_messages_from_store(store, session_id, WORKSPACE)
    if not messages:
        return SavedTurn(started=False, result=None)

    last = messages[-1].message
    result = (
        "".join(block["text"] for block in last["content"] if block["type"] == "text")
        if last.get("stop_reason") == "end_turn"
        else None
    )
    return SavedTurn(started=True, result=result)
