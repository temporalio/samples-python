"""Unit tests for the Python triage activity's tool registry.

Drives the registry directly with `MockProvider.run_loop` — bypasses
`agentic_session` (which would require a real Anthropic client). Asserts that
the agent's tool-call sequence produces the expected final result.

No API keys, no Temporal, no shell exec, no MCP HTTP — all stubbed via the
injected `TriageDeps`.

Mirrors workers/typescript/triage_activity.test.ts.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from temporalio.contrib.tool_registry.testing import ResponseBuilder

from triage_activity import build_triage_registry, TriageDeps
from triage_types import AlertPayload, ApprovalResponse


# ── Fixtures ────────────────────────────────────────────────────────────────


def make_alert() -> AlertPayload:
    return AlertPayload(
        status="firing",
        labels={"alertname": "HighLatencyP99", "service": "api", "runbook": "rollback-or-scale"},
        annotations={"summary": "P99 > 1s", "description": "P99 above threshold for 1m."},
        startsAt=datetime.now(timezone.utc).isoformat(),
    )


def make_deps(**overrides: Any) -> TriageDeps:
    async def default_list(base_url: str) -> list[dict[str, Any]]:
        if "7071" in base_url:
            return [{
                "name": "prometheus_query",
                "description": "instant PromQL query",
                "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
            }]
        return [{
            "name": "kubectl_describe",
            "description": "describe a k8s resource",
            "inputSchema": {
                "type": "object",
                "properties": {"resource": {"type": "string"}, "name": {"type": "string"}, "namespace": {"type": "string"}},
                "required": ["resource", "name"],
            },
        }]

    async def default_call(_url: str, name: str, args: dict[str, Any]) -> str:
        return f"(mocked {name} → {args})"

    async def default_approve(_alert: AlertPayload, _req: Any) -> ApprovalResponse:
        return ApprovalResponse(decision="approved", reason="default-mock")

    async def default_exec(cmd: str) -> tuple[str, str]:
        return f"(mocked exec: {cmd})", ""

    deps = TriageDeps(
        mcp_list_tools=overrides.get("mcp_list_tools", default_list),
        mcp_call_tool=overrides.get("mcp_call_tool", default_call),
        request_human_approval=overrides.get("request_human_approval", default_approve),
        exec_shell_command=overrides.get("exec_shell_command", default_exec),
    )
    return deps


class FakeSession:
    """Stub for AgenticSession with just .results so build_triage_registry works."""
    def __init__(self) -> None:
        self.results: list[Any] = []


async def async_run_loop(script: list[dict[str, Any]], registry: Any) -> None:
    """Async variant of MockProvider.run_loop.

    The shipped MockProvider uses sync `registry.dispatch()` which rejects async
    handlers (TypeError). Our triage handlers are async (httpx, asyncio
    subprocess, Temporal client). This helper iterates the same script but
    calls `await registry.adispatch(...)` instead.
    """
    for response in script:
        if response.get("_mock_stop"):
            return
        for block in response.get("content", []):
            if block.get("type") == "tool_use":
                await registry.adispatch(block["name"], block.get("input", {}))


async def drive(deps: TriageDeps, script: list[dict[str, Any]]) -> tuple[Any, list[Any]]:
    session = FakeSession()
    registry, get_result = await build_triage_registry(make_alert(), session, deps)
    await async_run_loop(script, registry)
    return get_result(), session.results


# ── Tests ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_happy_path_resolved():
    """investigate → propose → approve → execute → report_resolved."""
    approval_calls = 0
    async def counting_approve(_alert: AlertPayload, _req: Any) -> ApprovalResponse:
        nonlocal approval_calls
        approval_calls += 1
        return ApprovalResponse(decision="approved", reason="go ahead")

    deps = make_deps(request_human_approval=counting_approve)
    action = "kubectl rollout restart deploy/api -n demo-app"

    result, mcp_results = await drive(deps, [
        ResponseBuilder.tool_call("prometheus_query", {"query": "up{service='api'}"}),
        ResponseBuilder.tool_call("kubectl_describe", {"resource": "pod", "name": "api-xyz", "namespace": "demo-app"}),
        ResponseBuilder.tool_call("propose_remediation", {"action": action, "justification": "leak; restart reclaims memory"}),
        ResponseBuilder.tool_call("request_human_approval", {
            "message": "Restart api?", "diagnosis": "memory leak", "proposedAction": action,
        }),
        ResponseBuilder.tool_call("execute_remediation", {"action": action}),
        ResponseBuilder.tool_call("report_resolved", {"summary": "restarted; latency normal"}),
        ResponseBuilder.done("done"),
    ])

    assert result.status == "resolved"
    assert "restart" in result.summary
    assert len(result.remediations) == 1
    assert result.remediations[0].action == action
    assert approval_calls == 1
    kinds = [r["kind"] for r in mcp_results]
    assert kinds == ["remediation", "approval", "executed", "final"]


@pytest.mark.asyncio
async def test_rejected_approval_unresolved():
    """Operator rejects → agent reports unresolved with reason in session results."""
    async def reject(_alert: AlertPayload, _req: Any) -> ApprovalResponse:
        return ApprovalResponse(decision="rejected", reason="off-hours; defer until tomorrow")

    deps = make_deps(request_human_approval=reject)

    result, mcp_results = await drive(deps, [
        ResponseBuilder.tool_call("propose_remediation", {"action": "kubectl scale ...", "justification": "transient"}),
        ResponseBuilder.tool_call("request_human_approval", {
            "message": "Scale?", "diagnosis": "transient", "proposedAction": "kubectl scale ...",
        }),
        ResponseBuilder.tool_call("report_unresolved", {"summary": "operator deferred"}),
        ResponseBuilder.done("done"),
    ])

    assert result.status == "unresolved"
    assert "deferred" in result.summary
    approval = next((r for r in mcp_results if r.get("kind") == "approval"), None)
    assert approval is not None
    assert approval["decision"] == "rejected"
    assert "off-hours" in approval["reason"]


@pytest.mark.asyncio
async def test_execute_refuses_without_approval():
    """Guard rail: execute_remediation rejects calls when no approval is in flight."""
    deps = make_deps()
    result, _ = await drive(deps, [
        ResponseBuilder.tool_call("execute_remediation", {"action": "rm -rf /"}),
        ResponseBuilder.tool_call("report_unresolved", {"summary": "tried to skip approval"}),
        ResponseBuilder.done("done"),
    ])
    assert result.status == "unresolved"


@pytest.mark.asyncio
async def test_execute_refuses_when_action_does_not_match():
    """Guard rail: execute_remediation rejects calls whose action ≠ approved one."""
    executed_cmd: list[str] = []
    async def record_exec(cmd: str) -> tuple[str, str]:
        executed_cmd.append(cmd)
        return "ran", ""

    deps = make_deps(
        request_human_approval=lambda a, r: _approve(a, r),
        exec_shell_command=record_exec,
    )

    async def _approve(_alert: AlertPayload, _req: Any) -> ApprovalResponse:
        return ApprovalResponse(decision="approved", reason="ok")

    result, _ = await drive(deps, [
        ResponseBuilder.tool_call("propose_remediation", {"action": "kubectl restart api", "justification": "x"}),
        ResponseBuilder.tool_call("request_human_approval", {
            "message": "Restart?", "diagnosis": "x", "proposedAction": "kubectl restart api",
        }),
        # Agent attempts a DIFFERENT action than what was approved.
        ResponseBuilder.tool_call("execute_remediation", {"action": "kubectl scale deploy/api --replicas=10"}),
        ResponseBuilder.tool_call("report_unresolved", {"summary": "guard tripped"}),
        ResponseBuilder.done("done"),
    ])

    assert result.status == "unresolved"
    assert executed_cmd == [], "exec_shell_command should not have been called"


@pytest.mark.asyncio
async def test_mcp_tools_registered():
    """Both MCP sidecars' tools + per-language tools all appear in the registry."""
    deps = make_deps()
    session = FakeSession()
    registry, _ = await build_triage_registry(make_alert(), session, deps)
    schemas = registry.to_anthropic()
    names = [t["name"] for t in schemas]
    for expected in [
        "prometheus_query", "kubectl_describe",
        "propose_remediation", "request_human_approval",
        "execute_remediation", "report_resolved", "report_unresolved",
    ]:
        assert expected in names, f"{expected} should be in registry"


@pytest.mark.asyncio
async def test_mcp_dispatch_forwards_to_sidecar():
    """Tool dispatch reaches mcp_call_tool with the right URL + name + args."""
    calls: list[dict[str, Any]] = []
    async def record_call(url: str, name: str, args: dict[str, Any]) -> str:
        calls.append({"url": url, "name": name, "args": args})
        return f"result for {name}"

    deps = make_deps(mcp_call_tool=record_call)

    await drive(deps, [
        ResponseBuilder.tool_call("prometheus_query", {"query": "up{}"}),
        ResponseBuilder.tool_call("report_unresolved", {"summary": "test"}),
        ResponseBuilder.done("done"),
    ])

    assert len(calls) == 1
    assert calls[0]["name"] == "prometheus_query"
    assert calls[0]["args"] == {"query": "up{}"}
    assert "7071" in calls[0]["url"]
