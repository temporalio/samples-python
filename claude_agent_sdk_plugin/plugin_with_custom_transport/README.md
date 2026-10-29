# Plugin with Custom Transport

Give Claude Code your own skill and MCP server by passing it a Claude Code plugin, and run Claude Code inside a [Docker Sandbox](https://docs.docker.com/ai/sandboxes/) instead of on the Worker.

A Claude Code plugin is a directory that bundles skills, MCP servers, agents, slash commands, and hooks. This sample's `haiku-writer` plugin has two parts:

- The `haiku` skill, which tells Claude to answer with a haiku signed `~ haiku-writer`, and to check it with `count_syllables` first.
- The `syllables` MCP server, which provides `count_syllables`. It uses only the standard library, so it runs on the sandbox's `python3` without installing anything.

```text
haiku-writer/
├── .claude-plugin/plugin.json
├── .mcp.json
├── servers/syllables.py
└── skills/haiku/SKILL.md
```

## What this shows

- **Your plugins work as they do in Claude Code.** Pass the plugin through `ClaudeAgentOptions.plugins`, and Claude picks up its skills and starts its MCP servers. The Workflow only has to allow the MCP tool, which Claude Code names `mcp__plugin_haiku-writer_syllables__count_syllables`.
- **Bring your own runtime.** A connector decides where Claude Code runs. `SandboxConnector` puts it in a Docker Sandbox, and the Workflow code doesn't change: it still uses a plain `TemporalTransport(options)`.
- **The connector owns the host's lifecycle.** `SandboxConnector` creates a sandbox for each Workflow, copies the plugin in before Claude Code starts, and removes the sandbox when Claude Code closes. The Workflow only names the plugin's path in the sandbox.
- **The API key stays out of history and out of the sandbox.** The Worker hands the key to the sandbox's proxy, and Claude Code only ever sees a placeholder.

## Prerequisites

[Docker Sandboxes](https://docs.docker.com/ai/sandboxes/) (`sbx`) installed on the Worker's machine and signed in (`sbx login`).

## Run it

All commands run from the repository root. Start a Temporal dev server in a separate terminal:

```bash
temporal server start-dev
```

Start the Worker in another terminal:

```bash
uv run --group claude-agent-sdk claude_agent_sdk_plugin/plugin_with_custom_transport/run_worker.py
```

The Worker runs offline: everything runs for real, including the sandbox and the plugin's MCP server, except the model, which follows a script. To use the real model, put `ANTHROPIC_API_KEY=...` in front of the command. This sample needs an API key: the sandbox's proxy doesn't take a `CLAUDE_CODE_OAUTH_TOKEN`.

Ask for a haiku from a third terminal:

```bash
temporal workflow execute \
  --type PluginWithCustomTransportWorkflow \
  --task-queue claude-agent-sdk-plugin-with-custom-transport \
  --workflow-id plugin-with-custom-transport \
  --input '"Write a haiku about durable execution."'
```

## Expected behavior

The result is a haiku followed by the `~ haiku-writer` signature. Offline it is always:

```text
Workers fall and rise
history remembers all
the work carries on

~ haiku-writer
```

Offline, the model's replies are scripted, but the skill and the MCP server run for real in the sandbox. Open the run in the Temporal UI to see them:

- The `claude-agent-sdk-connect` Activity's input includes `--plugin-dir` and the plugin's path in the sandbox.
- The `claude-agent-sdk-read` Activities carry the skill's text and the MCP server's counts, `5`, `7`, and `5`.

Live, the wording is Claude's, and the signature shows Claude followed the skill.

While the Workflow runs, `sbx ls` shows its `claude-sandbox-...` sandbox. Once the Workflow completes, the sandbox is gone.

## Files

| File | Description |
|------|-------------|
| `haiku-writer/` | The plugin: the `haiku` skill and the `syllables` MCP server |
| `connector.py` | `SandboxConnector`, which copies uploads into a sandbox and runs Claude Code there through `sbx` |
| `workflow.py` | `PluginWithCustomTransportWorkflow`: `ClaudeSDKClient` with the plugin |
| `run_worker.py` | Registers `ClaudeAgentSDKPlugin(connector=SandboxConnector(uploads=...))` and the offline answers |
