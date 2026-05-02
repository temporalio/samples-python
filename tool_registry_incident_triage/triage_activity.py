"""triage_incident_activity — the agentic loop (Python port).

Mirrors workers/typescript/activities/triage.ts:
  - Pulls Prometheus + Kubernetes tools from MCP sidecars (localhost:7071/7072)
    via JSON-RPC over HTTP, registers them on the ToolRegistry.
  - Defines per-language tools: propose_remediation, request_human_approval,
    execute_remediation, report_resolved, report_unresolved.
  - Opens an agentic_session, runs the loop, returns the parsed result.

Structure for testability:
  - build_triage_registry() returns the (registry, get_result) pair. Pure-ish:
    takes all I/O dependencies as injected callables so unit tests can
    substitute them.
  - triage_incident_activity() opens the agentic_session, calls
    build_triage_registry with real deps, runs the LLM loop.
"""
from __future__ import annotations

import asyncio
import dataclasses
import json
import os
import subprocess
from typing import Any, Awaitable, Callable

import httpx
from temporalio import activity
from temporalio.client import Client
from temporalio.common import WorkflowIDConflictPolicy
from temporalio.contrib.tool_registry import (
    ToolRegistry,
    agentic_session,
)

from approval_workflow import ApprovalWorkflow
from triage_types import (
    AlertPayload,
    ApprovalRequest,
    ApprovalResponse,
    ProposedRemediation,
    TriageResult,
)


SYSTEM_PROMPT = """You are an SRE on-call agent triaging a production alert.

You have these tools (sourced from MCP sidecars + per-language helpers):
  - prometheus_query(query)            instant PromQL query
  - prometheus_query_range(query, start, end, step)
  - prometheus_alerts()                what is currently firing
  - kubectl_get(resource, namespace?)  list K8s resources
  - kubectl_describe(resource, name, namespace?)
  - kubectl_logs(pod, namespace, tail?)
  - propose_remediation(action, justification)   record but do NOT execute
  - request_human_approval(message, diagnosis, proposedAction)
                                       blocks until operator says approve|reject
  - execute_remediation(action)        ONLY callable AFTER approval was approved.
                                       Pass the same action you got approved.
  - report_resolved(summary)           ends the loop with status=resolved
  - report_unresolved(summary)         ends the loop with status=unresolved

Workflow:
  1. Read the alert. Use prometheus_query to confirm the symptom is currently true.
  2. Use kubectl_get/describe/logs and prometheus_query_range to find root cause.
  3. propose_remediation with a specific action.
  4. request_human_approval, attaching your diagnosis and the proposed action.
  5. If approved: execute_remediation, then prometheus_query to verify, then report_resolved.
  6. If rejected: report_unresolved with the operator's reason.

Be terse. Conversation history is heartbeated to Temporal — keep tool inputs short.
"""


# ── Injectable dependencies (override in tests) ────────────────────────────


@dataclasses.dataclass
class TriageDeps:
    """Pluggable I/O for the triage activity. Tests substitute their own."""

    mcp_list_tools: Callable[[str], Awaitable[list[dict[str, Any]]]]
    mcp_call_tool: Callable[[str, str, dict[str, Any]], Awaitable[str]]
    request_human_approval: Callable[[AlertPayload, ApprovalRequest], Awaitable[ApprovalResponse]]
    exec_shell_command: Callable[[str], Awaitable[tuple[str, str]]]


async def _mcp_list_tools(base_url: str) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.post(
            base_url,
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        )
        data = r.json()
        if "error" in data:
            raise RuntimeError(f"mcp tools/list {base_url}: {data['error']['message']}")
        return data.get("result", {}).get("tools", []) or []


async def _mcp_call_tool(base_url: str, name: str, args: dict[str, Any]) -> str:
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            base_url,
            json={
                "jsonrpc": "2.0",
                "id": int(asyncio.get_event_loop().time() * 1000),
                "method": "tools/call",
                "params": {"name": name, "arguments": args},
            },
        )
        data = r.json()
        if "error" in data:
            return f"MCP error: {data['error']['message']}"
        blocks = data.get("result", {}).get("content", []) or []
        return "\n".join(b.get("text", "") for b in blocks)


async def _exec_shell_command(cmd: str) -> tuple[str, str]:
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
    except asyncio.TimeoutError:
        proc.kill()
        raise
    return stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace")


def default_deps() -> TriageDeps:
    return TriageDeps(
        mcp_list_tools=_mcp_list_tools,
        mcp_call_tool=_mcp_call_tool,
        request_human_approval=_real_request_human_approval,
        exec_shell_command=_exec_shell_command,
    )


PROM_MCP = os.environ.get("MCP_PROMETHEUS_URL", "http://localhost:7071/")
K8S_MCP = os.environ.get("MCP_KUBERNETES_URL", "http://localhost:7072/")


# ── Registry builder (testable surface) ──────────────────────────────────────


async def build_triage_registry(
    alert: AlertPayload,
    session: Any,  # AgenticSession or test stub with .results: list
    deps: TriageDeps,
    *,
    prom_mcp: str = PROM_MCP,
    k8s_mcp: str = K8S_MCP,
) -> tuple[ToolRegistry, Callable[[], TriageResult | None]]:
    """Build a populated ToolRegistry plus a get_result() accessor.

    Pure modulo deps — MockProvider.run_loop(messages, registry) drives the
    registry without any real MCP, Temporal, or shell dependency.
    """
    registry = ToolRegistry()

    # MCP-sourced tools.
    try:
        prom_tools = await deps.mcp_list_tools(prom_mcp)
    except Exception:
        prom_tools = []
    try:
        k8s_tools = await deps.mcp_list_tools(k8s_mcp)
    except Exception:
        k8s_tools = []

    for tool in prom_tools:
        name = tool["name"]

        def make_handler(n: str) -> Callable[[dict[str, Any]], Awaitable[str]]:
            async def h(inp: dict[str, Any]) -> str:
                return await deps.mcp_call_tool(prom_mcp, n, inp)
            return h

        registry.handler({
            "name": name,
            "description": tool.get("description", ""),
            "input_schema": tool.get("inputSchema", {"type": "object"}),
        })(make_handler(name))

    for tool in k8s_tools:
        name = tool["name"]

        def make_handler(n: str) -> Callable[[dict[str, Any]], Awaitable[str]]:
            async def h(inp: dict[str, Any]) -> str:
                return await deps.mcp_call_tool(k8s_mcp, n, inp)
            return h

        registry.handler({
            "name": name,
            "description": tool.get("description", ""),
            "input_schema": tool.get("inputSchema", {"type": "object"}),
        })(make_handler(name))

    # Per-language tools.
    remediations: list[ProposedRemediation] = []
    approved_action: str | None = None
    final: TriageResult | None = None

    @registry.handler({
        "name": "propose_remediation",
        "description": "Record a remediation you would apply. Does NOT execute it.",
        "input_schema": {
            "type": "object",
            "properties": {"action": {"type": "string"}, "justification": {"type": "string"}},
            "required": ["action", "justification"],
        },
    })
    def propose(inp: dict[str, Any]) -> str:
        r = ProposedRemediation(action=str(inp["action"]), justification=str(inp["justification"]))
        remediations.append(r)
        session.results.append({"kind": "remediation", **dataclasses.asdict(r)})
        return "recorded"

    @registry.handler({
        "name": "request_human_approval",
        "description": "Block until operator decides. Returns JSON {decision, reason}.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "diagnosis": {"type": "string"},
                "proposedAction": {"type": "string"},
            },
            "required": ["message", "diagnosis", "proposedAction"],
        },
    })
    async def request_approval(inp: dict[str, Any]) -> str:
        nonlocal approved_action
        req = ApprovalRequest(
            message=str(inp["message"]),
            diagnosis=str(inp["diagnosis"]),
            proposedAction=str(inp["proposedAction"]),
        )
        response = await deps.request_human_approval(alert, req)
        if response.decision == "approved":
            approved_action = req.proposedAction
        session.results.append({"kind": "approval", **dataclasses.asdict(response)})
        return json.dumps(dataclasses.asdict(response))

    @registry.handler({
        "name": "execute_remediation",
        "description": "Execute the previously-approved action. Errors if no approval has been granted.",
        "input_schema": {
            "type": "object",
            "properties": {"action": {"type": "string"}},
            "required": ["action"],
        },
    })
    async def execute(inp: dict[str, Any]) -> str:
        action = str(inp["action"])
        if approved_action is None:
            return "ERROR: no approval has been granted. Call request_human_approval first."
        if action != approved_action:
            return f"ERROR: requested action does not match approved action. Approved: {approved_action}"
        try:
            stdout, stderr = await deps.exec_shell_command(action)
            session.results.append({
                "kind": "executed",
                "action": action,
                "stdout": stdout[:2000],
                "stderr": stderr[:2000],
            })
            return (stdout or stderr or "ok")[:4000]
        except Exception as e:  # noqa: BLE001
            return f"EXEC ERROR: {e}"

    @registry.handler({
        "name": "report_resolved",
        "description": "Ends the loop with status=resolved.",
        "input_schema": {
            "type": "object",
            "properties": {"summary": {"type": "string"}},
            "required": ["summary"],
        },
    })
    def report_resolved(inp: dict[str, Any]) -> str:
        nonlocal final
        final = TriageResult(status="resolved", summary=str(inp["summary"]), remediations=list(remediations))
        session.results.append({"kind": "final", **dataclasses.asdict(final)})
        return "ok"

    @registry.handler({
        "name": "report_unresolved",
        "description": "Ends the loop with status=unresolved.",
        "input_schema": {
            "type": "object",
            "properties": {"summary": {"type": "string"}},
            "required": ["summary"],
        },
    })
    def report_unresolved(inp: dict[str, Any]) -> str:
        nonlocal final
        final = TriageResult(status="unresolved", summary=str(inp["summary"]), remediations=list(remediations))
        session.results.append({"kind": "final", **dataclasses.asdict(final)})
        return "ok"

    return registry, lambda: final


def build_prompt(alert: AlertPayload) -> str:
    return (
        f"Alert fired: {alert.labels.get('alertname')} on {alert.labels.get('service', 'unknown')}.\n"
        f"Summary: {alert.annotations.get('summary', '(none)')}\n"
        f"Description: {alert.annotations.get('description', '(none)')}\n"
        f"Runbook hint: {alert.labels.get('runbook', '(none)')}\n\n"
        "Investigate, propose, get approval, and either fix or report unresolved."
    )


# ── Activity entrypoint ─────────────────────────────────────────────────────


@activity.defn(name="triage_incident_activity")
async def triage_incident_activity(alert: AlertPayload) -> TriageResult:
    deps = default_deps()
    async with agentic_session() as session:
        registry, get_result = await build_triage_registry(alert, session, deps)
        await session.run_tool_loop(
            registry=registry,
            provider="anthropic",
            system=SYSTEM_PROMPT,
            prompt=build_prompt(alert),
        )
        final = get_result()
        if final is None:
            raise RuntimeError("Agent ended the loop without calling report_resolved or report_unresolved")
        return final


# ── Real HITL bridge ─────────────────────────────────────────────────────────


async def _real_request_human_approval(
    alert: AlertPayload, request: ApprovalRequest
) -> ApprovalResponse:
    """signal_with_start ApprovalWorkflow with deterministic ID per alert group."""
    api_key = os.environ.get("TEMPORAL_API_KEY")
    address = os.environ.get("TEMPORAL_ADDRESS")
    namespace = os.environ.get("TEMPORAL_NAMESPACE")
    if not (api_key and address and namespace):
        raise RuntimeError("Missing TEMPORAL_ADDRESS / TEMPORAL_NAMESPACE / TEMPORAL_API_KEY")

    client = await Client.connect(
        address,
        namespace=namespace,
        rpc_metadata={"authorization": f"Bearer {api_key}"},
        tls=True,
    )

    key = f"{alert.labels.get('alertname', 'unknown')}-{alert.labels.get('service', 'unknown')}"
    approval_workflow_id = f"approval-{key.lower()}"
    task_queue = os.environ.get("TEMPORAL_TASK_QUEUE", "triage-python")

    handle = await client.start_workflow(
        ApprovalWorkflow.run,
        key,
        id=approval_workflow_id,
        task_queue=task_queue,
        start_signal="approval-request",
        start_signal_args=[request],
        # If the activity retries while the approval workflow is still running,
        # attach to the existing one rather than starting a new approval. The
        # operator should not get a second prompt for the same incident.
        id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
    )
    return await handle.result()
