"""Verify a ticket-triage trace in Langfuse via the public API.

Fetches the trace, reconstructs the observation tree, and deep-compares it
against the expected shape — including observation types — then checks that
every GENERATION carries a model and token usage, and that no observation was
duplicated (running the worker with --replay-stress surfaces replay-caused
duplicates here, if there were any).

Usage:
    python -m langfuse_tracing.verify_trace --trace-id <hex trace id>
    python -m langfuse_tracing.verify_trace --workflow-id <workflow id>
    python -m langfuse_tracing.verify_trace --trace-id <id> --expect declined

Stdlib-only on purpose so it is trivially copy-out-able.
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

# Expected observation trees as (depth, name, type) rows, children sorted by
# name under each parent. LLM spans are normalized to "<generation>" because
# their name depends on the instrumentation flavor ("ChatCompletion" for
# openinference, "chat <model>" for openai-v2); their type must always be
# GENERATION.
EXPECTED_APPROVED = [
    (0, "ticket-triage", "SPAN"),
    (1, "StartWorkflow:TicketTriageWorkflow", "SPAN"),
    (2, "RunWorkflow:TicketTriageWorkflow", "SPAN"),
    (3, "StartActivity:draft_reply", "SPAN"),
    (4, "RunActivity:draft_reply", "SPAN"),
    (5, "<generation>", "GENERATION"),
    (3, "triage", "SPAN"),
    (4, "StartActivity:classify_ticket", "SPAN"),
    (5, "RunActivity:classify_ticket", "SPAN"),
    (6, "<generation>", "GENERATION"),
    (4, "StartActivity:lookup_account", "SPAN"),
    (5, "RunActivity:lookup_account", "SPAN"),
    (1, "StartWorkflowUpdate:approve", "SPAN"),
    (2, "HandleUpdate:approve", "SPAN"),
    (2, "ValidateUpdate:approve", "SPAN"),
]
EXPECTED_DECLINED = [
    (0, "ticket-triage", "SPAN"),
    (1, "StartWorkflow:TicketTriageWorkflow", "SPAN"),
    (2, "RunWorkflow:TicketTriageWorkflow", "SPAN"),
    (3, "triage", "SPAN"),
    (4, "StartActivity:classify_ticket", "SPAN"),
    (5, "RunActivity:classify_ticket", "SPAN"),
    (6, "<generation>", "GENERATION"),
    (4, "StartActivity:lookup_account", "SPAN"),
    (5, "RunActivity:lookup_account", "SPAN"),
    (1, "StartWorkflowUpdate:approve", "SPAN"),
    (2, "HandleUpdate:approve", "SPAN"),
    (2, "ValidateUpdate:approve", "SPAN"),
]


def _api_get(path: str, params: Optional[dict[str, str]] = None) -> Any:
    host = os.environ.get("LANGFUSE_HOST", "http://localhost:3000").rstrip("/")
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
    if not public_key or not secret_key:
        raise SystemExit(
            "LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY must be set. Copy "
            "langfuse_tracing/.env.example to langfuse_tracing/.env and load it "
            "in this terminal: set -a; source langfuse_tracing/.env; set +a"
        )
    auth = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
    url = f"{host}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read())


def _fetch_trace(trace_id: str) -> Optional[dict[str, Any]]:
    try:
        return _api_get(f"/api/public/traces/{trace_id}")
    except urllib.error.HTTPError as err:
        if err.code == 404:
            return None
        raise


def _resolve_trace_id_by_workflow_id(workflow_id: str) -> Optional[str]:
    # The starter sets langfuse.session.id to the workflow ID on the root span.
    result = _api_get("/api/public/traces", {"sessionId": workflow_id, "limit": "10"})
    data = result.get("data") or []
    return data[0]["id"] if data else None


def _normalized_name(observation: dict[str, Any]) -> str:
    if observation.get("type") == "GENERATION":
        return "<generation>"
    return str(observation["name"])


def _build_tree(observations: list[dict[str, Any]]) -> list[tuple[int, str, str]]:
    children: dict[Optional[str], list[dict[str, Any]]] = {}
    for observation in observations:
        children.setdefault(observation.get("parentObservationId"), []).append(
            observation
        )
    rows: list[tuple[int, str, str]] = []

    def walk(observation: dict[str, Any], depth: int) -> None:
        rows.append((depth, _normalized_name(observation), str(observation["type"])))
        for child in sorted(
            children.get(observation["id"], []), key=lambda o: str(o["name"])
        ):
            walk(child, depth + 1)

    for root in sorted(children.get(None, []), key=lambda o: str(o["name"])):
        walk(root, 0)
    return rows


def _print_tree(rows: list[tuple[int, str, str]]) -> None:
    for depth, name, type_ in rows:
        print(f"    {'    ' * depth}{name}  [{type_}]")


def _poll_stable_trace(trace_id: str, timeout_seconds: int) -> dict[str, Any]:
    """Poll until the trace exists and its observation count is stable.

    Langfuse ingestion is asynchronous, so a freshly finished run may land
    over a few seconds even though export already succeeded.
    """
    deadline = time.monotonic() + timeout_seconds
    previous_count = -1
    while time.monotonic() < deadline:
        trace = _fetch_trace(trace_id)
        if trace is not None:
            count = len(trace.get("observations") or [])
            if count > 0 and count == previous_count:
                return trace
            previous_count = count
        time.sleep(2)
    raise SystemExit(
        f"FAIL: trace {trace_id} not fully ingested within {timeout_seconds}s"
    )


def _verify_trace(args: argparse.Namespace) -> int:
    trace_id = args.trace_id
    if not trace_id:
        trace_id = _resolve_trace_id_by_workflow_id(args.workflow_id)
        if not trace_id:
            print(f"FAIL: no trace found for workflow id {args.workflow_id}")
            return 1

    trace = _poll_stable_trace(trace_id, args.timeout)
    observations = trace.get("observations") or []
    failures: list[str] = []

    # 1. No duplicate observations (replay must not re-emit spans).
    ids = [o["id"] for o in observations]
    if len(set(ids)) != len(ids):
        failures.append("duplicate observation ids present")
    actual = _build_tree(observations)
    if len(set(actual)) != len(actual):
        failures.append(
            "duplicate (depth, name, type) rows — extra spans present (workflow "
            "replay must never re-emit spans; activity retries also add a "
            "RunActivity span per attempt)"
        )

    # 2. Whole-tree deep equality, types included.
    expected = EXPECTED_DECLINED if args.expect == "declined" else EXPECTED_APPROVED
    print(f"Trace {trace_id}: {len(observations)} observations")
    _print_tree(actual)
    if actual != expected:
        failures.append("tree mismatch")
        print("  Expected:")
        _print_tree(expected)

    # 3. Every GENERATION has a model and token usage.
    for observation in observations:
        if observation["type"] != "GENERATION":
            continue
        usage = observation.get("usage") or {}
        if not observation.get("model"):
            failures.append(f"GENERATION {observation['id']} missing model")
        if not usage.get("input") or not usage.get("output"):
            failures.append(f"GENERATION {observation['id']} missing token usage")
        if args.require_content and (
            observation.get("input") is None or observation.get("output") is None
        ):
            failures.append(
                f"GENERATION {observation['id']} missing input/output content"
            )

    # 4. Trace-level enrichment from the starter's root span.
    if trace.get("name") != "ticket-triage":
        failures.append(
            f"trace name is {trace.get('name')!r}, expected 'ticket-triage'"
        )
    if not trace.get("sessionId"):
        failures.append("trace has no session id (expected the workflow id)")
    if not trace.get("userId"):
        failures.append("trace has no user id")
    if "temporal" not in (trace.get("tags") or []):
        failures.append("trace missing 'temporal' tag")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: tree shape, observation types, generations, and enrichment all match")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace-id", help="Trace ID printed by the starter")
    parser.add_argument("--workflow-id", help="Workflow ID (resolved via session id)")
    parser.add_argument(
        "--expect", choices=["approved", "declined"], default="approved"
    )
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument(
        "--require-content",
        action="store_true",
        default=os.environ.get("LLM_INSTRUMENTATION", "openinference")
        == "openinference",
        help="Assert GENERATIONs carry input/output content "
        "(default true for openinference)",
    )
    args = parser.parse_args()

    if not args.trace_id and not args.workflow_id:
        parser.error("one of --trace-id or --workflow-id is required")
    return _verify_trace(args)


if __name__ == "__main__":
    sys.exit(main())
