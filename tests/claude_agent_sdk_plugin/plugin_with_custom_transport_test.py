import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

import claude_agent_sdk
import pytest
from temporalio.claude_agent_sdk import ClaudeAgentSDKPlugin
from temporalio.client import Client
from temporalio.worker import Replayer, Worker

from claude_agent_sdk_plugin.offline import scripted_api
from claude_agent_sdk_plugin.plugin_with_custom_transport.connector import (
    PROXY_MANAGED_KEY,
    SandboxConnector,
)
from claude_agent_sdk_plugin.plugin_with_custom_transport.run_worker import (
    HAIKU,
    LOCAL_PLUGIN_DIR,
    OFFLINE_ANSWERS,
)
from claude_agent_sdk_plugin.plugin_with_custom_transport.workflow import (
    COUNT_SYLLABLES,
    PLUGIN_DIR,
    PluginWithCustomTransportWorkflow,
)

SECRET = "sk-ant-test-secret-never-in-history"

FAKE_SBX = """#!{python}
import json, os, sys

ROOT = {root!r}
BIN = {bin!r}
args = sys.argv[1:]
with open(os.path.join(ROOT, "log.jsonl"), "a") as log:
    log.write(json.dumps(args) + "\\n")
sandboxes = os.path.join(ROOT, "sandboxes")
command = args[0]
if command == "ls":
    print("\\n".join(sorted(os.listdir(sandboxes))))
elif command == "create":
    name = args[args.index("--name") + 1]
    os.makedirs(os.path.join(sandboxes, name, "home/agent/workspace"))
elif command == "secret":
    name = args[args.index("--sandbox") + 1]
    with open(os.path.join(ROOT, "secrets.jsonl"), "a") as secrets:
        secrets.write(json.dumps([name, sys.stdin.read().strip()]) + "\\n")
elif command == "exec":
    rest = args[1:]
    env = {{"PATH": BIN + ":/usr/bin:/bin"}}
    workdir = "/home/agent/workspace"
    interactive = False
    while rest[0].startswith("-"):
        flag = rest.pop(0)
        if flag == "-i":
            interactive = True
        elif flag == "-e":
            key, _, value = rest.pop(0).partition("=")
            env[key] = value.replace("host.docker.internal", "127.0.0.1")
        elif flag == "-w":
            workdir = rest.pop(0)
    name, *argv = rest
    sandbox = os.path.join(sandboxes, name)
    if not os.path.isdir(sandbox):
        sys.exit("sandbox not found: " + name)
    home = os.path.join(sandbox, "home/agent")
    env["HOME"] = home
    argv = [home + arg[len("/home/agent"):] if arg.startswith("/home/agent") else arg for arg in argv]
    os.setsid()
    with open(os.path.join(sandbox, "groups"), "a") as groups:
        groups.write(str(os.getpid()) + "\\n")
    os.chdir(os.path.join(sandbox, workdir.lstrip("/")))
    if not interactive:
        os.dup2(os.open(os.devnull, os.O_RDONLY), 0)
    os.execvpe(argv[0], argv, env)
"""


@pytest.fixture
def fake_sbx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An `sbx` that runs each sandbox's commands in a temporary directory.

    Like the real sandbox, it has `claude` and `python3`: the Claude Code bundled
    with the Claude Agent SDK and the test's own Python.
    """
    root = tmp_path / "sbx"
    bin = root / "bin"
    bin.mkdir(parents=True)
    (root / "sandboxes").mkdir()
    (bin / "claude").symlink_to(
        Path(claude_agent_sdk.__file__).parent / "_bundled" / "claude"
    )
    (bin / "python3").symlink_to(sys.executable)
    script = bin / "sbx"
    script.write_text(
        FAKE_SBX.format(python=sys.executable, root=str(root), bin=str(bin))
    )
    script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin}{os.pathsep}{os.environ['PATH']}")
    return root


def sbx_calls(root: Path) -> list[list[str]]:
    return [json.loads(line) for line in (root / "log.jsonl").read_text().splitlines()]


def user_blocks(request: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        block
        for message in request["messages"]
        if message["role"] == "user" and isinstance(message["content"], list)
        for block in message["content"]
    ]


def tool_result(request: dict[str, Any], tool_use_id: str) -> dict[str, Any]:
    return next(
        block
        for block in user_blocks(request)
        if block.get("tool_use_id") == tool_use_id
    )


async def test_plugin_skill_and_mcp_server_run_from_the_copy_in_the_sandbox(
    client: Client, fake_sbx: Path
) -> None:
    task_queue = f"claude-agent-sdk-plugin-with-custom-transport-{uuid.uuid4()}"
    with scripted_api(OFFLINE_ANSWERS) as api:
        os.environ["ANTHROPIC_API_KEY"] = SECRET
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[PluginWithCustomTransportWorkflow],
            plugins=[
                ClaudeAgentSDKPlugin(
                    connector=SandboxConnector(uploads={PLUGIN_DIR: LOCAL_PLUGIN_DIR})
                )
            ],
        ):
            handle = await client.start_workflow(
                PluginWithCustomTransportWorkflow.run,
                "Write a haiku about durable execution.",
                id=f"claude-agent-sdk-plugin-with-custom-transport-{uuid.uuid4()}",
                task_queue=task_queue,
            )
            result = await handle.result()

    assert result == f"{HAIKU}\n\n~ haiku-writer"
    assert api.asked == ["haiku", "tool_result:toolu_skill", "tool_result:toolu_count"]

    first, second, third = api.requests
    assert sorted(t["name"] for t in first["tools"]) == ["Skill", COUNT_SYLLABLES]
    assert "- haiku-writer:haiku: Write the answer as a haiku." in json.dumps(first)

    # The skill's text reached Claude.
    assert tool_result(second, "toolu_skill")["content"] == (
        "Launching skill: haiku-writer:haiku"
    )
    skill_text = "\n".join(
        b["text"] for b in user_blocks(second) if b.get("type") == "text"
    )
    assert "count_syllables" in skill_text

    # The plugin's MCP server ran in the sandbox and answered.
    counts = json.dumps(tool_result(third, "toolu_count")["content"])
    assert "5: Workers fall and rise" in counts
    assert "7: history remembers all" in counts

    # Claude Code got the plugin's path in the sandbox, which only the upload filled.
    calls = sbx_calls(fake_sbx)
    [create] = [call for call in calls if call[0] == "create"]
    name = create[create.index("--name") + 1]
    upload = next(call for call in calls if call[0] == "exec" and "tar" in call[-3])
    launch = next(call for call in calls if call[0] == "exec" and "claude" in call)
    assert upload[-1] == PLUGIN_DIR
    assert calls.index(upload) < calls.index(launch)
    assert launch[launch.index("--plugin-dir") + 1] == PLUGIN_DIR

    # The key went to the sandbox's proxy, and Claude Code got a placeholder.
    assert f"ANTHROPIC_API_KEY={PROXY_MANAGED_KEY}" in launch
    secrets = [json.loads(line) for line in (fake_sbx / "secrets.jsonl").open()]
    assert [name, SECRET] in secrets

    # The sandbox outlives the Workflow, for the user to remove.
    assert (fake_sbx / "sandboxes" / name).exists()
    assert not any(call[0] == "rm" for call in calls)

    history = await handle.fetch_history()
    assert SECRET not in history.to_json()
    await Replayer(
        workflows=[PluginWithCustomTransportWorkflow], plugins=[ClaudeAgentSDKPlugin()]
    ).replay_workflow(history)
